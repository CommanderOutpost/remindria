from db import db  # Import the initialized db object
from bson.objectid import ObjectId
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

# Collection reference
other_collection = db["others"]


# Other schema
class OtherModel:
    """
    Represents a piece of information that's not a schedule in the application, encapsulating all relevant details for other useful information.

    Attributes:
        user_id (str): The ID of the user the information belongs to (foreign key reference to Users).
        content (str): The content of the information.
        seen (bool, optional): Indicates whether the information has been seen by the AI. Defaults to False.
        created_at (datetime, optional): The timestamp when the information was created. Defaults to the current UTC time.
        updated_at (datetime, optional): The timestamp when the information was last updated. Defaults to the current UTC time.

    Methods:
        to_dict():
            Converts the OtherModel instance to a dictionary format suitable for MongoDB insertion.
    """

    def __init__(
        self,
        user_id,
        content,
        seen=False,
        created_at=None,
        updated_at=None,
    ):
        """
        Initializes a new OtherModel instance.

        Args:
        user_id (str): The ID of the user the information belongs to (foreign key reference to Users).
        content (str): The content of the information.
        seen (bool, optional): Indicates whether the information has been seen by the AI. Defaults to False.
        created_at (datetime, optional): The timestamp when the information was created. Defaults to the current UTC time.
        updated_at (datetime, optional): The timestamp when the information was last updated. Defaults to the current UTC time.
        """
        self.user_id = user_id  # Foreign key from Users (ObjectId reference)
        self.content = content  # Content of the information
        self.seen = False  # Seen status, defaults to False
        self.created_at = created_at or datetime.now(timezone.utc)  # Creation timestamp
        self.updated_at = updated_at or datetime.now(
            timezone.utc
        )  # Last update timestamp

    def to_dict(self):
        """
        Converts the OtherModel instance to a dictionary format for MongoDB insertion.

        Returns:
            dict: A dictionary representation of the information, with the following keys:
                - "user_id" (ObjectId): The ID of the user (converted to ObjectId).
                - "content" (str): The content of the information.
                - "seen" (bool): The seen status of the information.
                - "created_at" (datetime): The creation timestamp of the information.
                - "updated_at" (datetime): The last update timestamp of the information.
        """
        return {
            "user_id": ObjectId(self.user_id),
            "content": self.content,
            "seen": self.seen,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Function to create a new piece of information
def create_other(other_data):
    """
    Inserts a new piece of information into the MongoDB collection.

    Args:
        other_data (dict): A dictionary containing the information details. Must include:
            - user_id (str): The ID of the user the information belongs to.
            - content (str): The content of the information.
            - status (str, optional): The status of the information (default is "Unseen").

    Returns:
        str: The ID of the newly created information as a string.

    Raises:
        ValueError: If required fields are missing or invalid.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate required fields
        required_fields = ["user_id", "content"]
        for field in required_fields:
            if field not in other_data or not other_data[field]:
                raise ValueError(f"'{field}' is a required field and cannot be empty.")

        # Create and insert the information
        other = OtherModel(**other_data)
        result = other_collection.insert_one(other.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to create other information: {e}")


# Function to find information by ID
def find_other_by_id(other_id):
    """
    Finds a piece of information by its unique MongoDB ID.

    Args:
        other_id (str): The ID of the information to find.

    Returns:
        dict: The information document if found, or None if no matching information exists.

    Raises:
        ValueError: If the provided other_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the other_id
        if not ObjectId.is_valid(other_id):
            raise ValueError(f"'{other_id}' is not a valid ObjectId.")

        # Find the information in the database
        other = other_collection.find_one({"_id": ObjectId(other_id)})
        if not other:
            return None
        return other

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to find other information with ID '{other_id}': {e}")


# Function to find all information for a user
def find_others_by_user_id(user_id):
    """
    Finds all pieces of information for a specific user.

    Args:
        user_id (str): The ID of the user whose information needs to be fetched.

    Returns:
        list: A list of information documents associated with the user.

    Raises:
        ValueError: If the provided user_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the user_id
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")

        # Fetch all information for the user
        others = list(other_collection.find({"user_id": ObjectId(user_id)}))
        return others

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to fetch information for user ID '{user_id}': {e}")


# Function to update a piece of information by ID
def update_other(other_id, updates):
    """
    Updates a piece of information with the provided fields.

    Args:
        other_id (str): The ID of the information to update.
        updates (dict): A dictionary containing the fields to update.

    Returns:
        int: The number of documents modified (should be 0 or 1).

    Raises:
        ValueError: If the provided other_id is not a valid ObjectId or if updates are empty.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the other_id
        if not ObjectId.is_valid(other_id):
            raise ValueError(f"'{other_id}' is not a valid ObjectId.")

        # Ensure updates are provided
        if not updates or not isinstance(updates, dict):
            raise ValueError("The 'updates' argument must be a non-empty dictionary.")

        # Automatically update the `updated_at` timestamp
        updates["updated_at"] = datetime.now(timezone.utc)

        # Perform the update
        result = other_collection.update_one(
            {"_id": ObjectId(other_id)}, {"$set": updates}
        )
        return result.modified_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to update other information with ID '{other_id}': {e}")


def set_seen_to_true(other_ids):
    """
    Updates the seen of multiple `OtherModel` entries to True based on their IDs.

    Args:
        other_ids (list): A list of `OtherModel` IDs to update.

    Returns:
        int: The number of documents modified.

    Raises:
        ValueError: If the provided `other_ids` contains invalid ObjectId values.
        PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the IDs
        if not isinstance(other_ids, list):
            raise ValueError("`other_ids` must be a list of valid ObjectId strings.")

        # Convert string IDs to ObjectId
        object_ids = []
        for other_id in other_ids:
            if not ObjectId.is_valid(other_id):
                raise ValueError(f"Invalid ObjectId: {other_id}")
            object_ids.append(ObjectId(other_id))

        # Perform the update operation
        result = other_collection.update_many(
            {"_id": {"$in": object_ids}},
            {"$set": {"seen": True, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except PyMongoError as e:
        raise PyMongoError(f"Database Error: {e}")
    except Exception as e:
        raise Exception(f"Unexpected Error: {e}")


# Function to delete a piece of information by ID
def delete_other(other_id):
    """
    Deletes a piece of information by its unique MongoDB ID.

    Args:
        other_id (str): The ID of the information to delete.

    Returns:
        int: The number of documents deleted (should be 0 or 1).

    Raises:
        ValueError: If the provided other_id is not a valid ObjectId.
        pymongo.errors.PyMongoError: If there is a database-related error.
    """
    try:
        # Validate the other_id
        if not ObjectId.is_valid(other_id):
            raise ValueError(f"'{other_id}' is not a valid ObjectId.")

        # Perform the delete operation
        result = other_collection.delete_one({"_id": ObjectId(other_id)})
        return result.deleted_count

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}")
    except Exception as e:
        raise Exception(f"Failed to delete other information with ID '{other_id}': {e}")
