from db import db  # Import the initialized db object
from datetime import datetime
from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs

# Collection reference
user_collection = db["users"]


# User schema for validation
class UserModel:
    """
    Represents a user schema for validation and interaction with the database.

    Attributes:
        username (str): The user's unique username.
        email (str): The user's email address.
        phone_number (str): The user's phone number.
        nationality (str): The user's nationality.
        age (int): The user's age.
        creation_date (datetime, optional): The timestamp when the user was created.
            Defaults to the current UTC time if not provided.
        ai_id (str, optional): A foreign key reference to an AI document.

    Methods:
        to_dict():
            Converts the UserModel instance into a dictionary format suitable for
            insertion into MongoDB.
    """

    def __init__(
        self,
        username,
        email,
        password,
        phone_number,
        nationality,
        age,
        creation_date=None,
        ai_id=None,
    ):
        """
        Initializes a UserModel instance with the provided user data.

        Args:
            username (str): The user's unique username.
            email (str): The user's email address.
            password (str): The user's password.
            phone_number (str): The user's phone number.
            nationality (str): The user's nationality.
            age (int): The user's age.
            creation_date (datetime, optional): The timestamp when the user was created.
                Defaults to the current UTC time if not provided.
            ai_id (str, optional): A foreign key reference to an AI document.
        """
        self.username = username
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.nationality = nationality
        self.age = age
        self.creation_date = creation_date or datetime.utcnow()
        self.ai_id = ai_id  # Foreign key reference to AI document

    def to_dict(self):
        """
        Converts the UserModel instance to a dictionary.

        Returns:
            dict: A dictionary representation of the UserModel instance, formatted for
            insertion into MongoDB with the following keys:
                - "username" (str): The user's username.
                - "email" (str): The user's email.
                - "phone_number" (str): The user's phone number.
                - "nationality" (str): The user's nationality.
                - "age" (int): The user's age.
                - "creation_date" (datetime): The timestamp when the user was created.
                - "ai_id" (str, optional): A foreign key reference to an AI document.
        """
        return {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "phone_number": self.phone_number,
            "nationality": self.nationality,
            "age": self.age,
            "creation_date": self.creation_date,
            "ai_id": self.ai_id,
        }


def create_user(user_data):
    """
    Inserts a new user document into the MongoDB collection.

    Args:
        user_data (dict): A dictionary containing user details with the following keys:
            - username (str): The username of the user.
            - email (str): The email address of the user.
            - password (str): The password of the user.
            - phone_number (str): The user's phone number.
            - nationality (str): The user's nationality.
            - age (int): The user's age.
            - ai_id (str, optional): A foreign key reference to an AI document.

    Returns:
        str: The unique ID of the newly created user document as a string.

    Raises:
        ValueError: If `user_data` is missing required fields or is not in the expected format.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate that required fields are present in user_data
        required_fields = [
            "username",
            "email",
            "password",
            "phone_number",
            "nationality",
            "age",
        ]
        missing_fields = [field for field in required_fields if field not in user_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Create a UserModel instance
        user = UserModel(**user_data)

        # Insert the user into the database
        result = user_collection.insert_one(user.to_dict())
        return str(result.inserted_id)

    except ValueError as ve:
        # Handle validation errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to create user: {e}") from e


def find_user_by_id(user_id):
    """
    Finds a user by their unique MongoDB ID.

    Args:
        user_id (str): The unique ID of the user as a string.

    Returns:
        dict: A dictionary representing the user document if found.
        None: If no user with the given ID exists.

    Raises:
        ValueError: If the `user_id` is not a valid MongoDB ObjectId string.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate that the user_id is a valid ObjectId
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user ID: {user_id}")

        # Query the database for the user
        user = user_collection.find_one({"_id": ObjectId(user_id)})
        return user

    except ValueError as ve:
        # Handle invalid ObjectId errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to find user by ID: {e}") from e


def find_all_users():
    """
    Fetches all users in the MongoDB collection.

    Returns:
        list: A list of dictionaries where each dictionary represents a user document.
              Returns an empty list if no users are found.

    Raises:
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Retrieve all user documents from the collection
        users = list(user_collection.find())
        return users

    except Exception as e:
        # Handle potential database operation failures
        raise Exception(f"Failed to fetch users: {e}") from e


def delete_user(user_id):
    """
    Deletes a user by their unique MongoDB ID.

    Args:
        user_id (str): The unique ID of the user as a string.

    Returns:
        dict: A dictionary containing the deletion result with the following keys:
            - "deleted_count" (int): The number of documents deleted (0 if no user was found).

    Raises:
        ValueError: If the `user_id` is not a valid MongoDB ObjectId string.
        pymongo.errors.PyMongoError: For any MongoDB operation failure.
    """
    try:
        # Validate that the user_id is a valid ObjectId
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user ID: {user_id}")

        # Perform the delete operation
        result = user_collection.delete_one({"_id": ObjectId(user_id)})

        # Return the result of the deletion
        return {"deleted_count": result.deleted_count}

    except ValueError as ve:
        # Handle invalid ObjectId errors
        raise ValueError(f"Validation Error: {ve}") from ve

    except Exception as e:
        # Handle other potential exceptions, including database errors
        raise Exception(f"Failed to delete user: {e}") from e
