from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI()


def get_ai_response(prompt, conversation_history, model="gpt-4o-mini"):
    """
    Generates a response from OpenAI, keeping track of conversation history.

    Parameters:
        prompt (str): User's input message.
        conversation_history (list): List of all previous messages in the conversation.

    Returns:
        str: AI's response.
    """
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": prompt})

    response = openai_client.chat.completions.create(
        model=model,
        messages=conversation_history,
    )

    # Extract the AI response
    ai_response = response.choices[0].message.content

    # Add the AI response to the conversation history
    conversation_history.append({"role": "assistant", "content": ai_response})

    return ai_response


# Initialize conversation history with the system prompt
# conversation_history = [
#     {
#         "role": "system",
#         "content": f"""You are a scheduling assistant called Remindria. Your job is to call people and tell them about their upcoming schedules.
#         The current user {user_info} has schedules {readable_schedules}. The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. You will greet the user and then after they respond,
#         you will tell them about their schedules.""",
#     }
# ]
