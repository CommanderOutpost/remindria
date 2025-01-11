from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
import json
from app.utils.helper import extract_json_from_text, parse_datetime, extract_speak_block
from config import config
from typing import Optional, Dict, Any, List
import datetime


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


def generate_action_response(
    action_type: str,
    success: bool,
    schedule_info: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    conversation_type: str = "chat",
    model: str = "gpt-4o-mini",
) -> str:
    """
    Calls the LLM to generate a user-facing response message after a schedule action
    (create/update/delete) either succeeded or failed.

    Args:
        action_type (str): "create", "update", or "delete"
        success (bool): Indicates if the action was successful
        schedule_info (dict): Info about the schedule (title, date/time, etc.)
        conversation_history (list): The conversation so far, or minimal context
                                     the AI might need (if you want it).
        conversation_type (str): "chat" or "call". If "call", produce SSML.
        model (str): The model name.

    Returns:
        str: The AI-generated message to the user about the action result.
    """

    # Shared basics for both chat/call
    base_instructions = (
        f"You are Remindria, a friendly scheduling assistant.\n"
        f"You have just performed a(n) {action_type.upper()} action on a schedule.\n"
        f"Success = {success}.\n"
        f"Schedule Info = {schedule_info}.\n\n"
    )

    if conversation_type == "call":
        # For phone-call style => produce SSML
        system_prompt = (
            "You must produce your entire response in valid SSML inside a single <speak>...</speak> block. "
            "Use friendly, casual language. Possibly use <prosody> or <break> for variety. "
            "No disclaimers or code blocks. Just SSML.\n\n"
            + base_instructions
            + "Generate a short summary of what happened with this schedule action. "
            "If success, you can say something upbeat; if fail, politely mention the issue. "
            "But always respond in SSML.\n"
            "You can use the following SSML features for realism:\n"
            "   - <prosody> for pitch/rate changes\n"
            "   - <break> to insert natural pauses\n"
            "   - <emphasis> to highlight key words\n"
            "   - volume/pitch variations for emotional effect\n"
        )
    else:
        # Normal chat => plain text
        system_prompt = (
            "You are Remindria, a friendly scheduling assistant. "
            "You have just performed an action on a schedule (create, update, or delete). "
            "Please produce a short, user-facing message in plain text. "
            "No disclaimers or code blocks.\n\n"
            + base_instructions
            + "Generate a short summary of what happened with this schedule action. "
            "If success, you can say something upbeat; if fail, mention the problem.\n"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        # If you want to pass existing conversation context, you could do so here:
        # for msg in conversation_history: messages.append(msg)
    ]

    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=200,
    )

    ai_text = response.choices[0].message.content.strip()
    if conversation_type == "call":
        ai_text = extract_speak_block(ai_text)

    return ai_text


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
) -> Optional[List[Dict[str, Any]]]:
    """
    Parses the entire conversation history to determine if the user intends
    to create, update, or delete one or more schedules (or none at all).

    Returns:
    --------
    - A list of schedule actions (each an action dict) of these forms:
      1) For new schedule:
         {
           "intent": "add_schedule",
           "schedule_title": str,
           "start_time": datetime,
           "end_time": datetime or None
         }

      2) For updating an existing schedule:
         {
           "intent": "update_schedule",
           "schedule_identifier": str,
           "existing_start_time": datetime or None,
           "new_title": str or None,
           "new_start_time": datetime or None,
           "new_end_time": datetime or None
         }

      3) For deleting an existing schedule:
         {
           "intent": "delete_schedule",
           "schedule_identifier": str,
           "existing_start_time": datetime or None
         }

    - If no recognized schedule operations, returns None.
    """

    # 1. Build a strong system prompt that instructs the LLM to always output a JSON array
    #    of objects (except "null" if no schedule action is recognized).
    system_prompt = (
        "You are a strict schedule-intent parser. You do NOT chat. You do NOT explain. "
        "You ONLY read the entire conversation below to see if the user wants to create, update, or delete schedules. "
        "\n\n"
        "Output EXACTLY one of the following:\n\n"
        "1) A JSON array of one or more objects (like `[ {...}, {...} ]`). "
        "   Each object in the array must be one of the following:\n"
        "   JSON for creating a schedule"
        "   {\n"
        '     "intent": "add_schedule",\n'
        '     "schedule_title": "Event Title",\n'
        '     "start_time": "YYYY-MM-DD HH:MM:SS",\n'
        '     "end_time": "YYYY-MM-DD HH:MM:SS"\n'
        '     "image": "image name" // optional, This is an image name describing what would be used to display\n'
        "   },\n"
        "   JSON for updating a schedule"
        "   {\n"
        '     "intent": "update_schedule",\n'
        '     "schedule_identifier": "existing schedule name",\n'
        '     "existing_start_time": "YYYY-MM-DD HH:MM:SS",\n'
        '     "new_title": "Updated Title" // optional,\n'
        '     "new_start_time": "YYYY-MM-DD HH:MM:SS" // optional,\n'
        '     "new_end_time": "YYYY-MM-DD HH:MM:SS" // optional\n'
        "   },\n"
        "   JSON for deleting a schedule"
        "   {\n"
        '     "intent": "delete_schedule",\n'
        '     "schedule_identifier": "existing schedule name",\n'
        '     "existing_start_time": "YYYY-MM-DD HH:MM:SS"\n'
        "   }\n\n"
        "2) The word 'null' (as a string) if no schedule creation, update, or delete is recognized.\n\n"
        "IMPORTANT:\n"
        "- You MUST NOT produce any text besides the JSON array or 'null'.\n"
        "- If there's no schedule-intent, or data is incomplete, output 'null' ONLY.\n"
        "- You do NOT wrap JSON in code fences. You do NOT add extra commentary.\n"
        "- Either a valid JSON array of objects or 'null'.\n"
        "- Even if there's only a single action, it must still be in an array like `[ {...} ]`.\n\n"
        "- The most recent information the user provides is what would be used.\n"
        "- For image name, you must only pick from the following: 'woman_taking_dog_on_walk', 'man_cooking', 'woman_cleaning', 'man_reading', 'woman_exercising'\n"
        "- Pick the image that best describes the schedule. If there isn't a good describing image for the current schedule, don't provide the image field.\n"
        "- You would assess the entire conversation to find out what the user wants to do and you would do it well."
        "- You will only return the json when the other AI asks for confirmation and the user accepts the confirmation."
        f"- The date and time right now is {datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")} \n"
        f"Schedules we are working with are: {schedules}"
    )

    # 2. Build the message sequence for the chat model
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        if msg["role"] != "system":
            messages.append({"role": msg["role"], "content": msg["content"]})

    # 3. Call the LLM
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
    print("\nRaw AI Response:\n", ai_text)

    # 4. Extract JSON from the AI response
    json_str = extract_json_from_text(ai_text)
    if not json_str:
        return None

    # 5. Parse the JSON. We expect either a JSON array or the string "null".
    try:
        parsed_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None

    # 6. If "null" (as a string) or data not recognized, return None
    #    (In some cases, the AI might produce the literal string 'null' within quotes)
    if isinstance(parsed_data, str) and parsed_data.lower() == "null":
        return None

    # 7. Our expected structure is a list of objects if not "null"
    if not isinstance(parsed_data, list):
        print("Parsed data is not a list - returning None.")
        return None

    final_actions = []

    # 8. Iterate through each object in the array
    for item in parsed_data:
        if not isinstance(item, dict):
            print("Array item is not a dict - invalid format.")
            return None

        intent = item.get("intent")

        # ADD SCHEDULE
        if intent == "add_schedule":
            start_dt = parse_datetime(item.get("start_time", ""))
            end_dt = (
                parse_datetime(item.get("end_time", ""))
                if item.get("end_time")
                else None
            )
            image = item.get("image", "")
            if not start_dt:
                print("No valid start_time found for add_schedule item.")
                return None
            action = {
                "intent": "add_schedule",
                "schedule_title": item.get("schedule_title", ""),
                "start_time": start_dt,
                "end_time": end_dt,
                "image": image,
            }
            final_actions.append(action)

        # UPDATE SCHEDULE
        elif intent == "update_schedule":
            schedule_id = item.get("schedule_identifier", "")
            existing_start_str = item.get("existing_start_time", "")
            new_title = item.get("new_title")
            new_start_str = item.get("new_start_time", "")
            new_end = (
                parse_datetime(item.get("new_end_time", ""))
                if item.get("new_end_time")
                else None
            )

            existing_start_dt = parse_datetime(existing_start_str)
            new_start_dt = parse_datetime(new_start_str)

            # If there's literally no update info:
            if not schedule_id and not new_title and not new_start_dt and not new_end:
                print("No update info provided for update_schedule item.")
                return None

            action = {
                "intent": "update_schedule",
                "schedule_identifier": schedule_id,
                "existing_start_time": existing_start_dt,
                "new_title": new_title,
                "new_start_time": new_start_dt,
                "new_end_time": new_end,
            }
            final_actions.append(action)

        # DELETE SCHEDULE
        elif intent == "delete_schedule":
            schedule_id = item.get("schedule_identifier", "")
            existing_start_str = item.get("existing_start_time", "")
            if not schedule_id:
                print("No schedule_id found for delete_schedule item.")
                return None

            existing_start_dt = parse_datetime(existing_start_str)
            action = {
                "intent": "delete_schedule",
                "schedule_identifier": schedule_id,
                "existing_start_time": existing_start_dt,
            }
            final_actions.append(action)

        else:
            # Unrecognized intent
            print(f"Unrecognized intent in item: {item}")
            return None
        
    print(final_actions)

    return final_actions if final_actions else None
