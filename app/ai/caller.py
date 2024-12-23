from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
from config import config

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
    print(summary)
    return summary
