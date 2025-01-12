from db import get_collection  # Import the initialized db object
from typing import Dict
from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs
from datetime import datetime, timezone  # Import datetime to handle timestamps

# Collection reference
schedule_records_collection = get_collection("schedule_records")


# ScheduleRecord schema
class ScheduleRecord:
    """
    Represents a schema for storing and interacting with schedule records in a MongoDB collection.
    Attributes:
        user_id (ObjectId): The ID of the user associated with the schedule record.
        action (str): The action performed (e.g., "create", "update", "delete").
        schedule_id (ObjectId): The ID of the associated schedule.
        created_at (datetime): The timestamp when the record was created.
    """

    def __init__(self, user_id: str, action: str, schedule_id: str, created_at=None):
        """
        Initializes a ScheduleRecord instance with the provided schedule record data.

        Args:
            user_id (str): The ID of the user associated with the schedule record.
            action (str): The action performed (e.g., "create", "update", "delete").
            schedule_id (str): The ID of the associated schedule.
            created_at (datetime): The timestamp when the record was created (default: current UTC time).
        """
        self.user_id = ObjectId(user_id)
        self.action = action
        self.schedule_id = ObjectId(schedule_id)
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, any]:
        """
        Converts the ScheduleRecord instance into a dictionary.

        Returns:
            dict: A dictionary representation of the ScheduleRecord instance, formatted for
            insertion into MongoDB with the following keys:
                - "user_id" (ObjectId): The ID of the user.
                - "action" (str): The action performed.
                - "schedule_id" (ObjectId): The ID of the associated schedule.
                - "created_at" (datetime): The timestamp when the record was created.
        """
        return {
            "user_id": self.user_id,
            "action": self.action,
            "schedule_id": self.schedule_id,
            "created_at": self.created_at,
        }


def add_record(record_data: Dict[str, any]) -> str:
    """
    Adds a new schedule record to the MongoDB collection.

    Args:
        record_data (dict): A dictionary containing schedule record details:
            - "user_id" (str): The ID of the user associated with the schedule record.
            - "action" (str): The action performed (e.g., "create", "update", "delete").
            - "schedule_id" (str): The ID of the associated schedule.

    Returns:
        str: The unique ID of the newly created record.

    Raises:
        ValueError: If required fields are missing or invalid.
        Exception: For any MongoDB operation failure.
    """
    try:
        # Validate required fields
        required_fields = ["user_id", "action", "schedule_id"]
        missing_fields = [
            field
            for field in required_fields
            if field not in record_data or not record_data[field]
        ]
        if missing_fields:
            raise ValueError(
                f"Missing or empty required fields: {', '.join(missing_fields)}"
            )

        # Create a ScheduleRecord instance
        record = ScheduleRecord(
            user_id=record_data["user_id"],
            date_time=record_data["date_time"],
            action=record_data["action"],
            schedule_id=record_data["schedule_id"],
        )

        # Insert into the database
        result = schedule_records_collection.insert_one(record.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve
    except Exception as e:
        raise Exception(f"Failed to add schedule record: {e}") from e


def find_all_records() -> list[Dict[str, any]]:
    """
    Retrieves all schedule records from the MongoDB collection.

    Returns:
        list: A list of dictionaries representing all schedule records in the collection.

    Raises:
        Exception: For any MongoDB operation failure.
    """
    try:
        # Fetch all records from the collection
        records = schedule_records_collection.find()

        # Convert MongoDB cursor to a list of dictionaries
        return [record for record in records]

    except Exception as e:
        raise Exception(f"Failed to retrieve schedule records: {e}") from e


def find_all_records_by_user_id(user_id: str) -> list[Dict[str, any]]:
    """
    Retrieves all schedule records for a specific user from the MongoDB collection.

    Args:
        user_id (str): The ID of the user whose records are to be retrieved.

    Returns:
        list: A list of dictionaries representing all schedule records for the user.

    Raises:
        ValueError: If the user_id is invalid.
        Exception: For any MongoDB operation failure.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        # Fetch all records for the given user_id
        records = schedule_records_collection.find({"user_id": ObjectId(user_id)})

        # Convert MongoDB cursor to a list of dictionaries
        return [record for record in records]

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve
    except Exception as e:
        raise Exception(f"Failed to retrieve records for user_id {user_id}: {e}") from e


def get_records_for_user_id_after_datetime(
    user_id: str, created_after: datetime
) -> list[Dict[str, any]]:
    """
    Retrieves all schedule records for a user created after a specific timestamp.

    Args:
        user_id (str): The ID of the user whose records are to be retrieved.
        created_after (datetime): The timestamp to filter records.

    Returns:
        list: A list of dictionaries representing all schedule records created after the given timestamp.

    Raises:
        ValueError: If the user_id is invalid or created_after is not a valid datetime object.
        Exception: For any MongoDB operation failure.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        # Validate created_after
        if not isinstance(created_after, datetime):
            raise ValueError("created_after must be a valid datetime object")

        # Fetch records for the given user_id created after the specified timestamp
        records = schedule_records_collection.find(
            {"user_id": ObjectId(user_id), "created_at": {"$gt": created_after}}
        )

        # Convert MongoDB cursor to a list of dictionaries
        return [record for record in records]

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve
    except Exception as e:
        raise Exception(
            f"Failed to retrieve records for user_id {user_id} after {created_after}: {e}"
        ) from e


def delete_record(user_id, record_id) -> int:
    """
    Deletes a schedule record from the MongoDB collection.

    Args:
        user_id (str): The ID of the user associated with the record.
        record_id (str): The ID of the record to be deleted.

    Returns:
        int: The number of records deleted (0 or 1).

    Raises:
        ValueError: If the user_id or record_id is invalid.
        Exception: For any MongoDB operation failure.
    """
    try:
        # Validate the user_id and record_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")
        if not ObjectId.is_valid(record_id):
            raise ValueError(f"Invalid record_id: {record_id}")

        # Delete the record with the given user_id and record_id
        result = schedule_records_collection.delete_one(
            {"user_id": ObjectId(user_id), "_id": ObjectId(record_id)}
        )

        return result.deleted_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve
    except Exception as e:
        raise Exception(
            f"Failed to delete record {record_id} for user_id {user_id}: {e}"
        ) from e


def delete_all_records_by_user_id(user_id: str) -> int:
    """
    Deletes all schedule records for a specific user from the MongoDB collection.

    Args:
        user_id (str): The ID of the user whose records are to be deleted.

    Returns:
        int: The number of records deleted.

    Raises:
        ValueError: If the user_id is invalid.
        Exception: For any MongoDB operation failure.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        # Delete all records for the given user_id
        result = schedule_records_collection.delete_many({"user_id": ObjectId(user_id)})

        return result.deleted_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve
    except Exception as e:
        raise Exception(f"Failed to delete records for user_id {user_id}: {e}") from e
