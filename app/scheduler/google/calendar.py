from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone
import logging

def get_upcoming_events(access_token, max_results=100):
    """
    Retrieves upcoming events from the user's Google Calendar.

    Args:
        access_token (str): The Google API access token.
        max_results (int): Maximum number of events to retrieve.

    Returns:
        list: A list of event dictionaries containing event details.
    """
    events_list = []
    try:
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Create credentials from the access token
        creds = Credentials(token=access_token)

        # Initialize the Calendar API
        service = build("calendar", "v3", credentials=creds)

        # Current time in UTC
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

        # Define the time range for events (e.g., now to next 30 days)
        time_min = now
        time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

        logging.info(f"Fetching events from {time_min} to {time_max}")

        # Initialize parameters for the API request
        request = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        )

        while request is not None:
            events_result = request.execute()
            events = events_result.get('items', [])

            logging.info(f"Fetched {len(events)} events")

            for event in events:
                # Extract start and end times
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))

                # Parse start and end times
                start_datetime = None
                end_datetime = None

                if start:
                    try:
                        start_datetime = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    except ValueError as ve:
                        logging.warning(f"Invalid start time format for event {event.get('id')}: {ve}")
                
                if end:
                    try:
                        end_datetime = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    except ValueError as ve:
                        logging.warning(f"Invalid end time format for event {event.get('id')}: {ve}")

                event_details = {
                    'event_id': event.get('id'),
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description', ''),
                    'start_time': start_datetime,
                    'end_time': end_datetime,
                    'location': event.get('location', ''),
                    'html_link': event.get('htmlLink', ''),
                    'created': event.get('created', ''),
                    'updated': event.get('updated', ''),
                    'status': event.get('status', ''),
                    'organizer': event.get('organizer', {}).get('email', ''),
                }
                events_list.append(event_details)

            # Handle pagination
            request = service.events().list_next(request, events_result)

    except HttpError as error:
        logging.error(f"Google API HTTP Error: {error.resp.status} - {error.content}")
        raise Exception(f"An error occurred while fetching calendar events: {error}")
    except Exception as error:
        logging.error(f"Error fetching calendar events: {error}")
        raise Exception(f"An unexpected error occurred while fetching calendar events: {error}")

    logging.info(f"Total events fetched: {len(events_list)}")
    return events_list
