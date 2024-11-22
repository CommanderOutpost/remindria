from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI()


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
    conversation_history.append({"role": "user", "content": prompt})

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
