from db import db, get_collection  # Import the initialized db object

# Collection reference
voice_settings_collection = get_collection(
    "voice_settings",
    indexes=[
        [("name", 1)],
        [("language", 1)],
    ],
)


# VoiceSettings schema
class VoiceSettingsModel:
    """
    Represents a schema for storing and interacting with voice settings in a MongoDB collection.

    Attributes:
        name (str): The name of the AI voice (e.g., Siri, Alexa).
        voice (str): The voice type or identifier (e.g., Male, Female, or specific voice model).
        language (str): The language associated with the voice (e.g., English, Yoruba).

    Methods:
        to_dict():
            Converts the VoiceSettingsModel instance into a dictionary format suitable for
            MongoDB insertion.
    """

    def __init__(self, name, voice, language):
        """
        Initializes a VoiceSettingsModel instance with the provided voice setting data.

        Args:
            name (str): The name of the AI voice (e.g., Siri, Alexa).
            voice (str): The voice type or identifier (e.g., Male, Female, or specific voice model).
            language (str): The language associated with the voice (e.g., English, Yoruba).
        """
        self.name = name
        self.voice = voice
        self.language = language

    def to_dict(self):
        """
        Converts the VoiceSettingsModel instance into a dictionary.

        Returns:
            dict: A dictionary representation of the VoiceSettingsModel instance, formatted for
            insertion into MongoDB with the following keys:
                - "name" (str): The name of the AI voice.
                - "voice" (str): The type or identifier of the voice.
                - "language" (str): The associated language.
        """
        return {
            "name": self.name,
            "voice": self.voice,
            "language": self.language,
        }


def create_voice_setting(data):
    """
    Inserts a new voice setting into the MongoDB collection.

    Args:
        data (dict): A dictionary containing voice setting details with the following keys:
            - "name" (str): The name of the AI voice (e.g., Siri, Alexa).
            - "voice" (str): The voice type or identifier (e.g., Male, Female, or specific voice model).
            - "language" (str): The language associated with the voice (e.g., English, Yoruba).

    Returns:
        str: The unique ID of the newly created voice setting document as a string.

    Raises:
        ValueError: If `data` is missing required fields or is not in the expected format.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate that required fields are present in data
        required_fields = ["name", "voice", "language"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Create a VoiceSettingsModel instance
        voice_setting = VoiceSettingsModel(**data)

        # Insert the voice setting into the database
        result = voice_settings_collection.insert_one(voice_setting.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        # Handle validation errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to create voice setting: {e}") from e


def find_voice_setting_by_id(voice_id):
    """
    Finds a voice setting by its unique MongoDB ID.

    Args:
        voice_id (str): The unique ID of the voice setting as a string.

    Returns:
        dict: A dictionary representing the voice setting document if found.
        None: If no voice setting with the given ID exists.

    Raises:
        ValueError: If the `voice_id` is not a valid MongoDB ObjectId string.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs

    try:
        # Validate that the voice_id is a valid ObjectId
        if not ObjectId.is_valid(voice_id):
            raise ValueError(f"Invalid voice ID: {voice_id}")

        # Query the database for the voice setting
        voice_setting = voice_settings_collection.find_one({"_id": ObjectId(voice_id)})
        return voice_setting

    except ValueError as ve:
        # Handle invalid ObjectId errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to find voice setting by ID: {e}") from e


def find_all_voice_settings():
    """
    Fetches all voice settings in the MongoDB collection.

    Returns:
        list: A list of dictionaries where each dictionary represents a voice setting document.
              Returns an empty list if no voice settings are found.

    Raises:
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Retrieve all voice setting documents from the collection
        voice_settings = list(voice_settings_collection.find())
        return voice_settings

    except Exception as e:
        # Handle database operation failures
        raise Exception(f"Failed to fetch all voice settings: {e}") from e


def delete_voice_setting(voice_id):
    """
    Deletes a voice setting by its unique MongoDB ID.

    Args:
        voice_id (str): The unique ID of the voice setting as a string.

    Returns:
        int: The number of documents deleted (1 if successful, 0 if no matching document is found).

    Raises:
        ValueError: If the `voice_id` is not a valid MongoDB ObjectId string.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs

    try:
        # Validate that the voice_id is a valid ObjectId
        if not ObjectId.is_valid(voice_id):
            raise ValueError(f"Invalid voice ID: {voice_id}")

        # Perform the delete operation
        result = voice_settings_collection.delete_one({"_id": ObjectId(voice_id)})
        return result.deleted_count

    except ValueError as ve:
        # Handle invalid ObjectId errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to delete voice setting: {e}") from e
