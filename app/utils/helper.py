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

    print(schedules)

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

    print("\n\n\n\n\n")
    print(messages)
    print("\n\n\n\n\n")

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
    print("\n\n\n\n")
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


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Attempt to parse a datetime from string. Return None if fails.
    """
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    # fallback to dateparser
    dt = dateparser.parse(dt_str)
    return dt


def extract_speak_block(text: str) -> str:
    """
    Extracts only the first <speak>...</speak> block from 'text' and returns it.
    Removes any content before or after that block.

    If no <speak> block is found, returns an empty string.
    """
    # Regex to capture the <speak>...some content...</speak> block
    pattern = re.compile(r"(<speak>.*?</speak>)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1)  # entire <speak>...</speak> block
    else:
        return ""  # or return None, depending on your needs
