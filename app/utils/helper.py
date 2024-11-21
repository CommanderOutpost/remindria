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
