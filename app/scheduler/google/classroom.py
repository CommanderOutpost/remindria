from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.utils.helper import clean_google_announcement_text


def get_upcoming_coursework(access_token):
    """
    Retrieves coursework due after today's date and time using an access token.

    Args:
        access_token (str): Google API access token.

    Returns:
        list: A list of dictionaries containing reminder messages and schedule details.
    """
    results = []
    try:
        # Create credentials from the access token
        creds = Credentials(token=access_token)

        # Initialize the Classroom API
        service = build("classroom", "v1", credentials=creds)

        # Retrieve the list of courses
        courses_result = service.courses().list().execute()
        courses = courses_result.get("courses", [])

        if not courses:
            return results

        # Iterate through each course to get coursework
        for course in courses:
            course_name = course["name"]
            course_id = course["id"]

            # Retrieve the coursework for the course
            coursework_result = (
                service.courses().courseWork().list(courseId=course_id).execute()
            )
            coursework = coursework_result.get("courseWork", [])

            if coursework:
                for work in coursework:
                    # Check if dueDate and dueTime are available
                    due_date = work.get("dueDate")
                    due_time = work.get(
                        "dueTime", {"hours": 23, "minutes": 59}
                    )  # Default to 11:59 PM
                    if due_date:
                        # Convert due date and time into a datetime object
                        due_datetime = datetime(
                            due_date["year"],
                            due_date["month"],
                            due_date["day"],
                            due_time.get("hours", 0),
                            due_time.get("minutes", 0),
                        )

                        # Compare with current time
                        if due_datetime > datetime.now():
                            reminder_message = (
                                f"Course: {course_name}\n"
                                f"Coursework: {work['title']}\n"
                                f"Description: {work.get('description', 'No description')}\n"
                                f"Due: {due_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            )
                            result = {
                                "reminder_message": reminder_message,
                                "due_date": due_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            results.append(result)
    except Exception as error:
        raise Exception(f"An error occurred: {error}")

    return results


def get_recent_announcements(access_token, minutes=10):
    """
    Retrieves announcements from Google Classroom made within the last specified minutes.

    Args:
        access_token (str): Google API access token.
        minutes (int): Time range in minutes to check for announcements. Default is 10.

    Returns:
        list: A list of dictionaries containing course name, announcement text, and creation time.
    """
    results = []
    try:
        # Create credentials from the access token
        creds = Credentials(token=access_token)

        # Initialize the Classroom API
        service = build("classroom", "v1", credentials=creds)

        # Retrieve the list of courses
        courses_result = service.courses().list().execute()
        courses = courses_result.get("courses", [])

        if not courses:
            return results

        # Define the time range
        now = datetime.now(timezone.utc)  # Google API times are in UTC
        time_range_start = now - timedelta(minutes=minutes)

        # Iterate through each course to get announcements
        for course in courses:
            course_name = course["name"]
            course_id = course["id"]

            # Retrieve the announcements for the course
            announcements_result = (
                service.courses().announcements().list(courseId=course_id).execute()
            )
            announcements = announcements_result.get("announcements", [])

            for announcement in announcements:
                creation_time_str = announcement.get("creationTime")
                creation_time = datetime.fromisoformat(
                    creation_time_str.replace("Z", "+00:00")
                )  # Convert ISO 8601 string to datetime object

                # Check if the announcement falls within the specified time range
                if time_range_start <= creation_time <= now:
                    result = {
                        "announcement_id": announcement["id"],
                        "course_name": course_name,
                        "update_time": announcement.get("updateTime", "No update time"),
                        "announcement_text": clean_google_announcement_text(
                            announcement.get("text", "No text provided")
                        ),
                        "creation_time": creation_time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    results.append(result)
    except Exception as error:
        raise Exception(f"An error occurred: {error}")

    return results
