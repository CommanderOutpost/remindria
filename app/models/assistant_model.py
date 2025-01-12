from db import get_collection  # Import the initialized db object
from typing import Dict
from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs

# Collection reference
voice_settings_collection = get_collection("assistants")


# Assistants schema
class AssistantsModel:
    """
    Represents a schema for storing and interacting with voice settings in a MongoDB collection.
    Attributes:
        name (str): The name of the AI voice (e.g., Siri, Alexa).
        voice (str): The voice of the assistant (e.g., specific voice model).
        language (str): The language of the assistant (e.g., English, Yoruba).
        personality (str): The personality of the assistant (e.g., personality description).
        image (str): The image of the assistant (e.g., image URL).
    """

    def __init__(
        self, name: str, voice: str, language: str, personality: str, image: str
    ):
        """
        Initializes a AssistantsModel instance with the provided voice setting data.

        See class docstring for attribute details.
        """
        self.name = name
        self.voice = voice
        self.language = language
        self.personality = personality
        self.image = image

    def to_dict(self) -> Dict[str, str]:
        """
        Converts the AssistantsModel instance into a dictionary.

        Returns:
            dict: A dictionary representation of the AssistantsModel instance, formatted for
            insertion into MongoDB with the following keys:
                - "name" (str): The name of the assistant.
                - "voice" (str): The type or identifier of the voice.
                - "language" (str): The language of the model.
                - "personality" (str): The personality of the assistant (e.g., personality description).
                - "image" (str): The image of the assistant.
        """
        return {
            "name": self.name,
            "voice": self.voice,
            "language": self.language,
            "personality": self.personality,
            "image": self.image,
        }


def create_assistant(data: Dict[str, str]) -> str:
    """
    Inserts a new assistant into the MongoDB collection.

    Args:
        data (dict): A dictionary containing assistant details with the following keys:
            - "name" (str): The name of the AI assistant (e.g., Siri, Alexa).
            - "voice" (str): The voice type or identifier (e.g., Male, Female, or specific voice model).
            - "language" (str): The language associated with the assistant (e.g., English, Yoruba).
            - "personality" (str): The personality of the assistant (e.g., friendly, formal, witty).
            - "image" (str): The image URL of the assistant.

    Returns:
        str: The unique ID of the newly created assistant document as a string.

    Raises:
        ValueError: If `data` is missing required fields or is not in the expected format.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate that all required fields are present in data
        required_fields = ["name", "voice", "language", "personality", "image"]
        missing_fields = [
            field for field in required_fields if field not in data or not data[field]
        ]
        if missing_fields:
            raise ValueError(
                f"Missing or empty required fields: {', '.join(missing_fields)}"
            )

        # Create an AssistantsModel instance
        assistant = AssistantsModel(**data)

        # Insert the assistant into the database
        result = voice_settings_collection.insert_one(assistant.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        # Handle validation errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to create assistant: {e}") from e


def update_assistant(assistant_id: str, update_data: Dict[str, str]) -> bool:
    """
    Updates an existing assistant in the MongoDB collection.

    Args:
        assistant_id (str): The unique ID of the assistant to be updated.
        update_data (dict): A dictionary containing the fields to be updated with their new values.

    Returns:
        bool: True if the update was successful, False otherwise.

    Raises:
        ValueError: If `assistant_id` is invalid or `update_data` is empty.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate input
        if not ObjectId.is_valid(assistant_id):
            raise ValueError("Invalid assistant ID.")
        if not update_data:
            raise ValueError("No update data provided.")

        # Optional: Validate keys in update_data
        valid_fields = {"name", "voice", "language", "personality", "image"}
        invalid_fields = [key for key in update_data if key not in valid_fields]
        if invalid_fields:
            raise ValueError(
                f"Invalid fields in update data: {', '.join(invalid_fields)}"
            )

        # Perform the update operation
        result = voice_settings_collection.update_one(
            {"_id": ObjectId(assistant_id)}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise ValueError("Assistant ID not found.")

        # Return whether the update was successful
        return result.modified_count > 0

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        raise Exception(f"Failed to update assistant: {e}") from e


def find_assistant_by_id(assistant_id: str) -> Dict[str, str] | None:
    """
    Retrieves an assistant from the MongoDB collection by its unique ID.

    Args:
        assistant_id (str): The unique ID of the assistant to retrieve.

    Returns:
        dict: A dictionary representing the assistant if found, or None if not found.

    Raises:
        ValueError: If `assistant_id` is invalid.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate the ID format
        if not ObjectId.is_valid(assistant_id):
            raise ValueError("Invalid assistant ID.")

        # Fetch the document with the given ID
        assistant = voice_settings_collection.find_one({"_id": ObjectId(assistant_id)})

        # Return the assistant as a dictionary, or None if not found
        return assistant

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        raise Exception(f"Failed to retrieve assistant: {e}") from e


def find_all_assistants(
    sort_by: str = "name", ascending: bool = True
) -> list[Dict[str, str]]:
    """
    Retrieves all assistants from the MongoDB collection, sorted by a specified field.

    Args:
        sort_by (str): The field to sort by (default is "name").
        ascending (bool): Whether to sort in ascending order (default is True).

    Returns:
        list: A list of dictionaries representing all assistants in the collection, sorted as specified.

    Raises:
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Determine sorting order
        sort_order = 1 if ascending else -1

        # Fetch all documents from the collection and apply sorting
        assistants = voice_settings_collection.find().sort(sort_by, sort_order)

        # Convert the MongoDB cursor to a list of dictionaries
        return [assistant for assistant in assistants]

    except Exception as e:
        raise Exception(f"Failed to retrieve assistants: {e}") from e


def get_all_assistant_names() -> list[str]:
    """
    Retrieves the names of all assistants from the MongoDB collection.

    Returns:
        list: A list of strings representing the names of all assistants.

    Raises:
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Fetch only the "name" field for all documents
        assistants = voice_settings_collection.find({}, {"name": 1, "_id": 0})

        # Extract and return the names
        return [assistant["name"] for assistant in assistants]

    except Exception as e:
        raise Exception(f"Failed to retrieve assistant names: {e}") from e


def get_assistant_personality_by_id(assistant_id: str) -> str | None:
    """
    Retrieves the personality of an assistant from the MongoDB collection by its unique ID.

    Args:
        assistant_id (str): The unique ID of the assistant to retrieve the personality for.

    Returns:
        str: The personality of the assistant if found, or None if no assistant matches the given ID.

    Raises:
        ValueError: If `assistant_id` is invalid.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate the ID format
        if not ObjectId.is_valid(assistant_id):
            raise ValueError("Invalid assistant ID.")

        # Fetch the assistant's personality
        assistant = voice_settings_collection.find_one(
            {"_id": ObjectId(assistant_id)}, {"personality": 1, "_id": 0}
        )

        # Return the personality if found, or None otherwise
        return assistant.get("personality") if assistant else None

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        raise Exception(f"Failed to retrieve assistant personality: {e}") from e


def delete_assistant(assistant_id: str) -> bool:
    """
    Deletes an existing assistant from the MongoDB collection.

    Args:
        assistant_id (str): The unique ID of the assistant to be deleted.

    Returns:
        bool: True if the deletion was successful, False otherwise.

    Raises:
        ValueError: If `assistant_id` is invalid.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate input
        if not ObjectId.is_valid(assistant_id):
            raise ValueError("Invalid assistant ID.")

        # Perform the delete operation
        result = voice_settings_collection.delete_one({"_id": ObjectId(assistant_id)})

        # Return whether the deletion was successful
        return result.deleted_count > 0

    except ValueError as ve:
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        raise Exception(f"Failed to delete assistant: {e}") from e
