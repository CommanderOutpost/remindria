from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
import json
from app.utils.helper import extract_json_from_text, parse_datetime
from config import config
from typing import Optional, Dict, Any, List


load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI()

openai_model = config.OPENAI_MODEL

enc = tiktoken.encoding_for_model(openai_model)


def generate_chat_title(
    user_info, schedules_readable, not_seen_others_readable, seen_others_readable
):
    """
    Generates a descriptive title for the chat based on user information and schedules.

    Parameters:
        user_info (dict): Dictionary containing user information.
        schedules_readable (str): Human-readable string of the user's schedules.
        not_seen_others_readable (str): Human-readable string of new additional information.
        seen_others_readable (str): Human-readable string of already communicated information.

    Returns:
        str: Generated chat title.
    """
    title_prompt = (
        "Based on the following user's first message, create a short and descriptive title for this chat.\n\n"
        f"User: {user_info['username']}\n"
        # f"Schedules: {schedules_readable}\n"
        # f"New Information: {not_seen_others_readable}\n"
        # f"Previously Discussed Information: {seen_others_readable}\n\n"
        "Title:"
    )

    # Initialize a temporary conversation history for title generation
    temp_history = [
        {
            "role": "system",
            "content": "You are an assistant that creates concise and descriptive titles for user chats based on provided context. Make sure, it's short and without text formatting like markdown, just plain text. No quotes too.",
        },
        {"role": "user", "content": title_prompt},
    ]

    # Get the AI-generated title
    chat_title = get_ai_response(title_prompt, temp_history)

    return chat_title.strip()


def conversation_token_count(conversation):
    # Combine all messages into a single text block for counting
    all_text = ""
    for msg in conversation:
        # Include role markers in counting if desired, or just the content:
        all_text += f"{msg['role']}: {msg['content']}\n"
    # Encode and count tokens
    tokens = enc.encode(all_text)
    return len(tokens)


def get_ai_response(prompt, conversation_history, model="gpt-4o-mini"):
    """
    Generates a response from OpenAI, keeping track of conversation history.

    Parameters:
        prompt (str): The user's input message to the AI.
        conversation_history (list): List of dictionaries representing the conversation history.
                                     Each dictionary must contain 'role' and 'content' keys.
        model (str): The AI model to use (default is "gpt-4o-mini").

    Returns:
        str: AI's response message.
    """
    # Validate input
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("The 'prompt' parameter must be a non-empty string.")
    if not isinstance(conversation_history, list) or not all(
        isinstance(msg, dict) and "role" in msg and "content" in msg
        for msg in conversation_history
    ):
        raise ValueError(
            "The 'conversation_history' must be a list of dictionaries with 'role' and 'content' keys."
        )

    # Add the user's message to the conversation history
    # conversation_history.append({"role": "user", "content": prompt})

    # Call the OpenAI API
    response = openai_client.chat.completions.create(
        model=model,
        messages=conversation_history,
    )

    # Extract and return the AI's response
    ai_response = response.choices[0].message.content

    # Add the AI's response to the conversation history
    conversation_history.append({"role": "assistant", "content": ai_response})

    return ai_response


def summarize_with_ai(conversation_history):
    """
    Summarize the conversation using the AI API.
    """
    # We'll create a summary prompt that instructs the AI to summarize the conversation so far.
    # Extract all user and assistant messages excluding the system message.
    filtered_history = [
        msg for msg in conversation_history if msg["role"] in ["user", "assistant"]
    ]

    if not filtered_history:
        return "No previous conversation."

    # We create a prompt to summarize
    summary_prompt = (
        "Summarize the main points of the following conversation in a concise yet comprehensive way. "
        "Focus on the key details and user requests without losing essential context:\n\n"
        + "\n".join(
            [
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in filtered_history
            ]
        )
    )

    # Temporarily use a lightweight conversation format for summarization
    temp_history = [
        {
            "role": "system",
            "content": "You are a helpful assistant that summarizes conversations.",
        },
        {"role": "user", "content": summary_prompt},
    ]

    summary = get_ai_response(summary_prompt, temp_history)
    return summary


def parse_natural_language_instructions(
    conversation_history: List[Dict[str, str]], schedules
) -> Optional[Dict[str, Any]]:
    """
    Parses the entire conversation history to determine if the user intends
    to create or update a schedule (or neither).

    Possible return structures:
      - For new schedule:
        {
          "intent": "add_schedule",
          "schedule_title": "Event Title",
          "start_time": <datetime>,
          "end_time": <datetime or None>
        }
      - For updating an existing schedule:
        {
          "intent": "update_schedule",
          "schedule_identifier": "Name or ID of schedule to update",
          "new_title": <str or None>,
          "new_start_time": <datetime or None>,
          "new_end_time": <datetime or None>
        }
      - For deleting an existing schedule:
        {
          "intent": "delete_schedule",
          "schedule_identifier": "Name or ID of schedule to delete"
        }
      - None (if no schedule intent).
    """

    system_prompt = (
        "You are a strict schedule-intent parser. You do NOT chat. You do NOT explain. "
        "You ONLY read the entire conversation below to see if the user wants to create, update, or delete a schedule. "
        "\n\n"
        "Output EXACTLY one of the following:\n\n"
        "1) JSON for creating a schedule:\n"
        "   {\n"
        '     "intent": "add_schedule",\n'
        '     "schedule_title": "Event Title",\n'
        '     "start_time": "YYYY-MM-DD HH:MM:SS",\n'
        '     "end_time": "YYYY-MM-DD HH:MM:SS"  // optional\n'
        "   }\n\n"
        "2) JSON for updating a schedule:\n"
        "   {\n"
        '     "intent": "update_schedule",\n'
        '     "schedule_identifier": "existing schedule name",\n'
        '     "existing_start_time": "YYYY-MM-DD HH:MM:SS",\n'  # New field
        '     "new_title": "Updated Title" // optional,\n'
        '     "new_start_time": "YYYY-MM-DD HH:MM:SS" // optional,\n'
        '     "new_end_time": "YYYY-MM-DD HH:MM:SS" // optional\n'
        "   }\n\n"
        "3) JSON for deleting a schedule:\n"
        "   {\n"
        '     "intent": "delete_schedule",\n'
        '     "schedule_identifier": "existing schedule name",\n'
        '     "existing_start_time": "YYYY-MM-DD HH:MM:SS"\n'
        "   }\n\n"
        "4) The word 'null' (as a string) if no schedule creation, update, or delete is recognized.\n\n"
        "IMPORTANT:\n"
        "- You MUST NOT produce any other text or explanation.\n"
        "- If there's no schedule-intent, or data is incomplete, output 'null' ONLY.\n"
        "- You do not greet or thank or respond with any text besides the JSON or 'null'.\n"
        "- You do NOT wrap JSON in code fences. You do NOT add extra commentary. Either valid JSON or 'null'."
        f"Schedules we are working with are: {schedules}"
    )

    # Build the prompt for the LLM with your entire conversation:
    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation_history:
        if msg["role"] != "system":
            messages.append({"role": msg["role"], "content": msg["content"]})

    # print("\n\n\n\n\n")
    # print(messages)
    # print("\n\n\n\n\n")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=400,
        )
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None

    ai_text = response.choices[0].message.content.strip()
    print("\n")
    print("Raw AI Response:\n", ai_text)

    # Extract JSON from the AI response
    json_str = extract_json_from_text(ai_text)
    if not json_str:
        return None

    # Attempt to parse
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None

    # If it's "add_schedule"
    if parsed.get("intent") == "add_schedule":
        start_dt = parse_datetime(parsed.get("start_time", ""))
        end_dt = (
            parse_datetime(parsed.get("end_time", ""))
            if parsed.get("end_time")
            else None
        )
        if not start_dt:
            print("No valid start_time found.")
            return None

        return {
            "intent": "add_schedule",
            "schedule_title": parsed.get("schedule_title", ""),
            "start_time": start_dt,
            "end_time": end_dt,
        }

    # If it's "update_schedule"
    elif parsed.get("intent") == "update_schedule":
        schedule_id = parsed.get("schedule_identifier", "")
        existing_start_str = parsed.get("existing_start_time", "")
        new_title = parsed.get("new_title")
        new_start_str = parsed.get("new_start_time", "")
        new_end = (
            parse_datetime(parsed.get("new_end_time", ""))
            if parsed.get("new_end_time")
            else None
        )

        existing_start_dt = parse_datetime(existing_start_str)
        new_start_dt = parse_datetime(new_start_str)

        if not schedule_id and not new_title and not new_start_dt and not new_end:
            print("No update info provided.")
            return None

        return {
            "intent": "update_schedule",
            "schedule_identifier": schedule_id,
            "existing_start_time": existing_start_dt,
            "new_title": new_title,
            "new_start_time": new_start_dt,
            "new_end_time": new_end,
        }

    # If it's "delete_schedule"
    elif parsed.get("intent") == "delete_schedule":
        schedule_id = parsed.get("schedule_identifier", "")
        existing_start_str = parsed.get("existing_start_time", "")
        if not schedule_id:
            print("No schedule_id found.")
            return None

        existing_start_dt = parse_datetime(existing_start_str)

        return {
            "intent": "delete_schedule",
            "existing_start_time": existing_start_dt,
            "schedule_identifier": schedule_id,
        }

    # Otherwise, no recognized schedule intent
    return None
