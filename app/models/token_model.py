from config import config
from google.oauth2.credentials import Credentials
from db import db
from bson.objectid import ObjectId
from datetime import datetime, timezone

# Collection reference
tokens_collection = db["tokens"]


class TokenModel:
    """
    Represents an authentication token for external services.
    Attributes:
        user_id (str): The ID of the user associated with the token.
        service_name (str): The name of the service (e.g., "google").
        access_token (str): The access token for the service.
        refresh_token (str): The refresh token for the service.
        token_expiry (datetime): The expiration datetime of the access token.
        created_at (datetime): Timestamp of token creation.
        updated_at (datetime): Timestamp of last token update.
    """

    def __init__(
        self,
        user_id,
        service_name,
        access_token,
        refresh_token=None,
        token_expiry=None,
        created_at=None,
        updated_at=None,
    ):
        self.user_id = ObjectId(user_id)
        self.service_name = service_name
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "service_name": self.service_name,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Insert a new token
def create_token(token_data):
    try:
        token = TokenModel(**token_data)
        result = tokens_collection.insert_one(token.to_dict())
        return str(result.inserted_id)
    except Exception as e:
        raise Exception(f"Failed to create token: {e}")


# Find a token by user_id and service_name
def find_token_by_user_and_service(user_id, service_name):
    try:
        token = tokens_collection.find_one(
            {"user_id": ObjectId(user_id), "service_name": service_name}
        )
        return token
    except Exception as e:
        raise Exception(f"Failed to find token for user and service: {e}")


def find_tokens_by_user(user_id):
    try:
        tokens = tokens_collection.find({"user_id": ObjectId(user_id)})
        return tokens
    except Exception as e:
        raise Exception(f"Failed to find tokens for user: {e}")


# Update a token
def update_token(user_id, service_name, updates):
    try:
        updates["updated_at"] = datetime.now(timezone.utc)
        result = tokens_collection.update_one(
            {"user_id": ObjectId(user_id), "service_name": service_name},
            {"$set": updates},
        )
        return result.modified_count
    except Exception as e:
        raise Exception(f"Failed to update token: {e}")


# Delete a token
def delete_token(user_id, service_name):
    try:
        result = tokens_collection.delete_one(
            {"user_id": ObjectId(user_id), "service_name": service_name}
        )
        return result.deleted_count
    except Exception as e:
        raise Exception(f"Failed to delete token: {e}")


def create_creds_from_db(user_id, service_name="google"):
    """
    Creates Google API credentials from stored tokens in the database
    and client_id/client_secret from environment variables.

    Args:
        user_id (str): The user's ID in the database.
        service_name (str): The name of the service (default is "google").

    Returns:
        Credentials: Google API credentials object.

    Raises:
        Exception: If credentials are not found or invalid.
    """
    try:
        # Get client_id and client_secret from environment variables
        client_id = config.GOOGLE_CLIENT_ID
        client_secret = config.GOOGLE_CLIENT_SECRET

        if not client_id or not client_secret:
            raise Exception(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables."
            )

        # Retrieve the token for the user and service from the database
        token = tokens_collection.find_one(
            {"user_id": ObjectId(user_id), "service_name": service_name}
        )
        if not token:
            raise Exception(
                f"No token found for user {user_id} and service {service_name}."
            )

        # Create the credentials object
        creds = Credentials(
            token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        return creds

    except Exception as e:
        raise Exception(f"Failed to create credentials: {e}")
