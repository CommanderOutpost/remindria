# app/utils/helper.py
from datetime import datetime


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
