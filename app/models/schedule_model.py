from db import db, get_collection  # Import the initialized db object
from bson.objectid import ObjectId
from datetime import datetime, timezone, timedelta
from pymongo.errors import PyMongoError

# Collection reference
schedule_collection = get_collection(
    "schedules",
    indexes=[
        [("user_id", 1)],  # Index for filtering by user_id
        [("schedule_date", 1)],  # Index for filtering by schedule_date
    ],
)



# Schedule schema
class ScheduleModel:
    """
    Represents a schedule in the application, encapsulating all relevant details for a reminder.

    Attributes:
        user_id (str): The ID of the user the schedule belongs to (foreign key reference to Users).
        reminder_message (str): The message or note for the reminder.
        schedule_date (datetime): The date and time for the scheduled reminder.
        recurrence (str, optional): The recurrence pattern for the reminder. Can be:
            - None: No recurrence (default).
            - "Daily": The reminder repeats daily.
            - "Weekly": The reminder repeats weekly.
            - "Monthly": The reminder repeats monthly.
        status (str, optional): The current status of the schedule. Defaults to "Pending". Can be:
            - "Pending": The reminder is awaiting execution.
            - "Completed": The reminder has been executed successfully.
            - "Skipped": The reminder was skipped or missed.
        created_at (datetime, optional): The timestamp when the schedule was created. Defaults to the current UTC time.
        updated_at (datetime, optional): The timestamp when the schedule was last updated. Defaults to the current UTC time.

    Methods:
        to_dict():
            Converts the ScheduleModel instance to a dictionary format suitable for MongoDB insertion.
    """

    def __init__(
        self,
        user_id,
        reminder_message,
        schedule_date,
        recurrence=None,
        status="Pending",
        event_id=None,
        created_at=None,
        updated_at=None,
    ):
        """
        Initializes a new ScheduleModel instance.

        Args:
            user_id (str): The ID of the user the schedule belongs to (foreign key reference to Users).
            reminder_message (str): The message or note for the reminder.
            schedule_date (datetime): The date and time for the scheduled reminder.
            recurrence (str, optional): The recurrence pattern for the reminder. Defaults to None.
            status (str, optional): The current status of the schedule. Defaults to "Pending".
            created_at (datetime, optional): The timestamp when the schedule was created. Defaults to the current UTC time.
            updated_at (datetime, optional): The timestamp when the schedule was last updated. Defaults to the current UTC time.
        """
        self.user_id = user_id  # Foreign key from Users (ObjectId reference)
        self.reminder_message = reminder_message  # Text for the reminder
        self.schedule_date = schedule_date  # Date and time for the reminder
        self.recurrence = recurrence  # None/Daily/Weekly/Monthly
        self.status = status  # Pending, Completed, Skipped
        self.event_id = event_id  # Google Calendar event ID (if synced)
        self.created_at = created_at or datetime.now(timezone.utc)  # Creation timestamp
        self.updated_at = updated_at or datetime.now(
            timezone.utc
        )  # Last update timestamp

    def to_dict(self):
        """
        Converts the ScheduleModel instance to a dictionary format for MongoDB insertion.

        Returns:
            dict: A dictionary representation of the schedule, with the following keys:
                - "user_id" (ObjectId): The ID of the user (converted to ObjectId).
                - "reminder_message" (str): The message or note for the reminder.
                - "schedule_date" (datetime): The date and time for the scheduled reminder.
                - "recurrence" (str): The recurrence pattern for the reminder.
                - "status" (str): The current status of the schedule.
                - "created_at" (datetime): The creation timestamp of the schedule.
                - "updated_at" (datetime): The last update timestamp of the schedule.
        """
        schedule_dict = {
            # Existing fields...
            "user_id": ObjectId(self.user_id),
            "reminder_message": self.reminder_message,
            "schedule_date": self.schedule_date,
            "recurrence": self.recurrence,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.event_id:
            schedule_dict["event_id"] = self.event_id  # Add this line
        return schedule_dict


# Function to create a new schedule
def create_schedule(schedule_data):
    """
    Inserts a new schedule into the MongoDB collection.

    Args:
        schedule_data (dict): A dictionary containing the schedule details. Must include:
            - user_id (str): The ID of the user the schedule belongs to.
            - reminder_message (str): The message to remind the user.
            - schedule_date (datetime): The date and time for the reminder.
            - recurrence (str, optional): Recurrence type (e.g., "None", "Daily", "Weekly", "Monthly").
            - status (str, optional): The status of the schedule (default is "Pending").

    Returns:
        str: The ID of the newly created schedule as a string.

    Raises:
        ValueError: If required fields are missing or invalid.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate required fields
        required_fields = ["user_id", "reminder_message", "schedule_date"]
        for field in required_fields:
            if field not in schedule_data or not schedule_data[field]:
                raise ValueError(f"'{field}' is a required field and cannot be empty.")

        # Ensure schedule_date is a valid datetime object
        if not isinstance(schedule_data["schedule_date"], datetime):
            raise ValueError("'schedule_date' must be a valid datetime object.")

        # Create and insert the schedule
        schedule = ScheduleModel(**schedule_data)
        result = schedule_collection.insert_one(schedule.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to create schedule: {e}")


# Function to find a schedule by ID
def find_schedule_by_id(schedule_id):
    """
    Finds a schedule by its unique MongoDB ID.

    Args:
        schedule_id (str): The ID of the schedule to find.

    Returns:
        dict: The schedule document if found, or None if no matching schedule exists.

    Raises:
        ValueError: If the provided schedule_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the schedule_id
        if not ObjectId.is_valid(schedule_id):
            raise ValueError(f"'{schedule_id}' is not a valid ObjectId.")

        # Find the schedule in the database
        schedule = schedule_collection.find_one({"_id": ObjectId(schedule_id)})
        if not schedule:
            return None
        return schedule

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to find schedule with ID '{schedule_id}': {e}")


# Function to find all schedules for a user
def find_schedules_by_user_id(user_id, amount=None):
    """
    Finds schedules for a specific user, with an optional limit on the number of schedules.

    Args:
        user_id (str): The ID of the user whose schedules need to be fetched.
        amount (int, optional): The maximum number of schedules to fetch. If None, fetches all schedules.

    Returns:
        list: A list of schedule documents associated with the user.

    Raises:
        ValueError: If the provided user_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")

        # Fetch schedules for the user with an optional limit
        query = {"user_id": ObjectId(user_id)}
        if amount is None:
            schedules = list(schedule_collection.find(query))
        else:
            schedules = list(schedule_collection.find(query).limit(amount))
        return schedules

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to fetch schedules for user ID '{user_id}': {e}")


def get_schedules_within_range(user_id, time_range, range_type="days"):
    """
    Retrieves schedules for a specific user within a given time range.

    Args:
        user_id (str): The ID of the user whose schedules need to be fetched.
        time_range (int): The range of time (in hours, days, or minutes) to filter schedules.
        range_type (str): The unit of the time range. Can be "days", "hours", or "minutes".
                          Defaults to "days".

    Returns:
        list: A list of schedule documents within the specified time range.

    Raises:
        ValueError: If the provided user_id is not a valid ObjectId or if inputs are invalid.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")

        # Validate the range_type
        valid_range_types = {"days", "hours", "minutes"}
        if range_type not in valid_range_types:
            raise ValueError(
                f"'range_type' must be one of {valid_range_types}. Got '{range_type}'."
            )

        # Calculate the range in seconds based on the range_type
        now = datetime.now(timezone.utc)
        if range_type == "days":
            delta = timedelta(days=time_range)
        elif range_type == "hours":
            delta = timedelta(hours=time_range)
        elif range_type == "minutes":
            delta = timedelta(minutes=time_range)

        # Define the time window
        start_time = now
        end_time = now + delta

        # Fetch schedules within the range for the user
        schedules = list(
            schedule_collection.find(
                {
                    "user_id": ObjectId(user_id),
                    "schedule_date": {"$gte": start_time, "$lte": end_time},
                }
            )
        )

        return schedules

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to fetch schedules within range: {e}")


def get_schedules_in_date_range(user_id, start_date, end_date):
    """
    Retrieves schedules for a specific user within a given date range.

    Args:
        user_id (str): The ID of the user whose schedules need to be fetched.
        start_date (datetime): The start datetime of the range.
        end_date (datetime): The end datetime of the range.

    Returns:
        list: A list of schedule documents within the specified date range.

    Raises:
        ValueError: If the provided user_id is not a valid ObjectId.
        PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")

        # Ensure start_date and end_date are timezone-aware and in UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = start_date.astimezone(timezone.utc)

        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = end_date.astimezone(timezone.utc)

        # Fetch schedules within the date range for the user
        schedules = list(
            schedule_collection.find(
                {
                    "user_id": ObjectId(user_id),
                    "schedule_date": {"$gte": start_date, "$lte": end_date},
                }
            ).sort(
                "schedule_date", 1
            )  # Optional: sort by schedule_date ascending
        )

        return schedules

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except PyMongoError as pe:
        raise PyMongoError(f"Database Error: {pe}")
    except Exception as e:
        raise Exception(f"Failed to fetch schedules in date range: {e}")


def find_schedule_by_name_and_datetime(user_id, reminder_message, schedule_date):
    """
    Finds a schedule that belongs to the given user,
    has the specified reminder_message,
    and exactly matches the schedule_date (datetime).

    Args:
        user_id (str): The ID of the user.
        reminder_message (str): The schedule name or reminder_message we are looking for.
        schedule_date (datetime): The original date/time of the schedule.

    Returns:
        dict: The schedule document if found, or None if none match.
    """
    try:
        # 1) Validate user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")

        # 2) Make sure we have a valid datetime
        if not isinstance(schedule_date, datetime):
            raise ValueError("'schedule_date' must be a valid datetime object.")

        # 3) Query
        schedule = schedule_collection.find_one(
            {
                "user_id": ObjectId(user_id),
                "reminder_message": reminder_message,
                "schedule_date": schedule_date,
            }
        )

        return schedule  # could be None if not found

    except Exception as e:
        raise Exception(f"Failed to find schedule by name & datetime: {str(e)}")


# Function to update a schedule by ID
def update_schedule(schedule_id, updates):
    """
    Updates a schedule with the provided fields.

    Args:
        schedule_id (str): The ID of the schedule to update.
        updates (dict): A dictionary containing the fields to update.

    Returns:
        int: The number of documents modified (should be 0 or 1).

    Raises:
        ValueError: If the provided schedule_id is not a valid ObjectId or if updates are empty.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the schedule_id
        if not ObjectId.is_valid(schedule_id):
            raise ValueError(f"'{schedule_id}' is not a valid ObjectId.")

        # Ensure updates are provided
        if not updates or not isinstance(updates, dict):
            raise ValueError("The 'updates' argument must be a non-empty dictionary.")

        # Automatically update the `updated_at` timestamp
        updates["updated_at"] = datetime.now(timezone.utc)

        # Perform the update
        result = schedule_collection.update_one(
            {"_id": ObjectId(schedule_id)}, {"$set": updates}
        )
        return result.modified_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to update schedule with ID '{schedule_id}': {e}")


def delete_schedule(schedule_id):
    """
    Deletes a schedule by its unique MongoDB ID.

    Args:
        schedule_id (str): The ID of the schedule to delete.

    Returns:
        int: The number of documents deleted (should be 0 or 1).

    Raises:
        ValueError: If the provided schedule_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the schedule_id
        if not ObjectId.is_valid(schedule_id):
            raise ValueError(f"'{schedule_id}' is not a valid ObjectId.")

        # Perform the delete operation
        result = schedule_collection.delete_one({"_id": ObjectId(schedule_id)})
        return result.deleted_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to delete schedule with ID '{schedule_id}': {e}")
