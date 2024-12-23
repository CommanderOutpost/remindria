# app/utils/helper.py
from datetime import datetime
from openai import OpenAI
import json
import re
from typing import Optional, Dict, Any, List
import dateparser


openai_client = OpenAI()


def format_schedule_human_readable(schedule_data):
    """
    Converts a list of schedules into human-readable sentences.

    Args:
        schedule_data (dict): A dictionary containing the "schedules" key with a list of schedules.

    Returns:
        str: A human-readable summary of the schedules.
    """
    if not isinstance(schedule_data, dict) or "schedules" not in schedule_data:
        raise ValueError(
            "Invalid schedule data format. Expected a dictionary with 'schedules' key."
        )

    # If there are no schedules, return No schedules message
    if not schedule_data["schedules"]:
        return "No schedules found."

    sentences = []
    for schedule in schedule_data["schedules"]:
        # Extracting details
        reminder_message = schedule.get("reminder_message", "No message")
        schedule_date = schedule.get("schedule_date", "Unknown date")
        status = schedule.get("status", "Unknown status")
        recurrence = schedule.get("recurrence", "No recurrence")

        # Format schedule_date to a more human-friendly format
        if isinstance(schedule_date, datetime):
            # If it's already a datetime object, format it directly
            schedule_date_formatted = schedule_date.strftime("%A, %d %B %Y at %I:%M %p")
        else:
            try:
                # Try parsing the string into a datetime object
                schedule_date_parsed = datetime.strptime(
                    schedule_date, "%a, %d %b %Y %H:%M:%S %Z"
                )
                schedule_date_formatted = schedule_date_parsed.strftime(
                    "%A, %d %B %Y at %I:%M %p"
                )
            except (ValueError, TypeError):
                # If parsing fails, fallback to the raw string
                schedule_date_formatted = schedule_date

        # Construct the sentence
        sentence = (
            f"Reminder: '{reminder_message}' is scheduled for {schedule_date_formatted} "
            f"with a recurrence of '{recurrence}'. Status: {status}."
        )
        sentences.append(sentence)

    return "\n".join(sentences)


def format_others_human_readable(other_data):
    """
    Converts a list of others into human-readable sentences.

    Args:
        other_data (dict): A dictionary containing the "others" key with a list of other entries.

    Returns:
        str: A human-readable summary of the others.
    """
    if not isinstance(other_data, dict) or "others" not in other_data:
        raise ValueError(
            "Invalid other data format. Expected a dictionary with 'others' key."
        )

    # If there are no others, return No others message
    if not other_data["others"]:
        return "No announcements found."

    sentences = []
    for other in other_data["others"]:
        # Extracting details
        content = other.get("content", "No content available")
        created_at = other.get("created_at", "Unknown date")
        status = other.get("status", "Unknown status")

        # Format created_at to a more human-friendly format
        if isinstance(created_at, datetime):
            created_at_formatted = created_at.strftime("%A, %d %B %Y at %I:%M %p")
        else:
            try:
                # Try parsing the string into a datetime object
                created_at_parsed = datetime.strptime(
                    created_at, "%a, %d %b %Y %H:%M:%S %Z"
                )
                created_at_formatted = created_at_parsed.strftime(
                    "%A, %d %B %Y at %I:%M %p"
                )
            except (ValueError, TypeError):
                # If parsing fails, fallback to the raw string
                created_at_formatted = created_at

        # Construct the sentence
        sentence = (
            f"Content: {content}\n"
            f"Created At: {created_at_formatted}\n"
            f"Status: {status}."
        )
        sentences.append(sentence)

    return "\n\n".join(sentences)


def clean_google_announcement_text(text):
    """
    Cleans up the announcement text by removing artifacts like \xa0
    and fixing spacing issues.

    Args:
        text (str): The raw announcement text.

    Returns:
        str: The cleaned-up text.
    """
    # Replace non-breaking spaces with regular spaces
    text = text.replace("\xa0", " ")

    # Remove excessive spaces
    text = " ".join(text.split())

    return text


# app/utils/helper.py


def parse_natural_language_instructions(
    conversation_history: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    """
    Parses the entire conversation history to determine if the user intends
    to create a schedule. If so, extracts schedule details.

    Args:
        conversation_history (List[Dict[str, str]]): List of messages in the conversation.
            Each message is a dict with 'role' and 'content' keys.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with schedule details or None if no schedule intent is detected.
    """
    system_prompt = (
        "You are a helper that reads the entire conversation below. "
        "If the user is requesting to create a schedule, unify all references to date/time and event name. "
        "Do not output anything apart from the JSON format below. Not an explanation, not anything, just the JSON.\n"
        "Output JSON with this format:\n\n"
        "{\n"
        '  "intent": "add_schedule",\n'
        '  "schedule_title": "Event Title",\n'
        '  "start_time": "YYYY-MM-DD HH:MM:SS",\n'
        '  "end_time": "YYYY-MM-DD HH:MM:SS" // optional\n'
        "}\n"
        "If the user is NOT asking to create a schedule, or you lack enough info, just return 'null'."
        "NEVER assume a title or date/time. For example if the user says 'I need a schedule by 8pm today.' "
        "Don't think the title is 'Event Title' until the user says so."
        "Return 'null' until every detail is clearly mentioned." 
    )

    # Build messages for the LLM
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    # Include the entire conversation
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Call the OpenAI model
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=300,
        )
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None

    ai_text = response.choices[0].message.content.strip()

    # Debug: Print the raw AI response
    print("Raw AI Response:")
    print(ai_text)

    # Extract JSON from the AI response
    json_str = extract_json_from_text(ai_text)
    if not json_str:
        print("No JSON found in the AI response.")
        return None

    # Attempt to parse the JSON
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None

    # Validate the intent
    if parsed.get("intent") != "add_schedule":
        print(f"Unexpected intent value: {parsed.get('intent')}")
        return None

    # Parse datetime strings
    def parse_datetime(dt_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        print(f"Unrecognized datetime format: {dt_str}")
        return None

    start_dt = parse_datetime(parsed.get("start_time", "")) or None
    end_dt = parse_datetime(parsed.get("end_time", "")) or None

    # Ensure start_time was parsed successfully
    if not start_dt:
        print("Invalid or missing start_time format.")
        return None

    # Construct the final dictionary
    schedule = {
        "intent": parsed["intent"],
        "schedule_title": parsed.get("schedule_title", ""),
        "start_time": start_dt,
        "end_time": end_dt,
    }

    return schedule


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extracts the first JSON object found in the given text.

    Args:
        text (str): The text containing JSON.

    Returns:
        Optional[str]: The extracted JSON string or None if not found.
    """
    # Pattern to find JSON within code blocks like ```json ... ```
    code_block_pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    match = code_block_pattern.search(text)
    if match:
        return match.group(1)

    # If no code block, try to find the first JSON object
    json_pattern = re.compile(r"(\{.*\})", re.DOTALL)
    match = json_pattern.search(text)
    if match:
        return match.group(1)

    # No JSON found
    return None


def handle_schedule_collection(pending_schedule, pending_step, user_input):
    """
    Based on which step we are on (pending_step), try to extract that piece of info
    from user_input. Return updated (pending_schedule, pending_step, reply_msg).
    """
    # We can do something simpler, or use another parse function.
    # For example, if we are awaiting_title, we assume user_input is the title, etc.

    if pending_step == "awaiting_title":
        # We set the title
        # Maybe we do a quick parse or just directly take user_input as the title
        pending_schedule["title"] = user_input
        # Next step is the date/time
        pending_step = "awaiting_date"
        reply = f"Got it! The schedule title is '{user_input}'. Now, what date/time do you want for it?"
        return pending_schedule, pending_step, reply

    elif pending_step == "awaiting_date":
        # We might parse the date/time from user_input using your parse function
        # e.g. parse_natural_language_instructions but ignoring the 'intent' part
        dt = parse_a_datetime(user_input)  # you'll write a smaller parser
        if dt:
            pending_schedule["start_time"] = dt
            # Next step could be to ask if user wants an end time
            pending_step = "awaiting_end_time"
            reply = f"Okay, scheduled start is {dt.strftime('%Y-%m-%d %H:%M')}. Do you have an end time?"
        else:
            # We failed to parse the date
            reply = "I couldn't understand that date/time. Could you try again? (e.g. 'Tomorrow at 3pm')"
        return pending_schedule, pending_step, reply

    elif pending_step == "awaiting_end_time":
        # parse end time
        dt = parse_a_datetime(user_input)
        if dt:
            pending_schedule["end_time"] = dt
            # Now we have all we need => next step is done
            pending_step = None
            reply = "Great, I have all the info I need. Let me add this schedule now..."
        else:
            if "no end time" in user_input.lower():
                # If user said no end time, we skip
                pending_schedule["end_time"] = None
                pending_step = None
                reply = "No end time specified. Let me add this schedule now..."
            else:
                reply = (
                    "I couldn't parse that end time. Try again, or say 'no end time'."
                )
        return pending_schedule, pending_step, reply

    else:
        # We have no known step
        return (
            pending_schedule,
            pending_step,
            "I'm not sure what you're trying to do right now.",
        )


def parse_a_datetime(user_input: str):
    """
    A minimal parser for a single date/time from the user’s input.
    You can expand or just do some basic dateparser usage:
    """

    dt = dateparser.parse(user_input)
    return dt
