from config import config
from db import db, get_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone

# Collection reference
tokens_collection = get_collection(
    "tokens",
    indexes=[
        [("user_id", 1)],  # Index for filtering by user_id
        [("service_name", 1)],  # Index for filtering by service_name
    ],
)



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
