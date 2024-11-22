# app/models/chat_model.py

from db import db
from bson.objectid import ObjectId
from datetime import datetime, timezone

# Collection reference
chat_collection = db["chats"]


class ChatModel:
    """
    Represents a chat conversation between a user and the AI assistant.

    Attributes:
        user_id (ObjectId): The ID of the user who owns the chat.
        messages (list): A list of messages in the conversation. Each message is a dict with 'role' and 'content'.
        created_at (datetime): Timestamp when the chat was created.
        updated_at (datetime): Timestamp when the chat was last updated.
    """

    def __init__(self, user_id, messages=None, created_at=None, updated_at=None):
        self.user_id = ObjectId(user_id)
        self.messages = messages or []
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def create_chat(chat_data):
    """
    Creates a new chat in the database.

    Args:
        chat_data (dict): Contains user_id and optionally messages.

    Returns:
        str: The ID of the newly created chat.
    """
    try:
        chat = ChatModel(**chat_data)
        result = chat_collection.insert_one(chat.to_dict())
        return str(result.inserted_id)
    except Exception as e:
        raise Exception(f"Failed to create chat: {e}")


def find_chat_by_id(chat_id):
    """
    Finds a chat by its ID.

    Args:
        chat_id (str): The ID of the chat.

    Returns:
        dict: The chat document if found, else None.
    """
    try:
        if not ObjectId.is_valid(chat_id):
            raise ValueError(f"'{chat_id}' is not a valid ObjectId.")
        chat = chat_collection.find_one({"_id": ObjectId(chat_id)})
        return chat
    except Exception as e:
        raise Exception(f"Failed to find chat by ID: {e}")


def find_chats_by_user_id(user_id):
    """
    Finds all chats for a user.

    Args:
        user_id (str): The ID of the user.

    Returns:
        list: List of chat documents.
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")
        chats = list(chat_collection.find({"user_id": ObjectId(user_id)}))
        return chats
    except Exception as e:
        raise Exception(f"Failed to find chats for user: {e}")


def add_message_to_chat(chat_id, message):
    """
    Adds a message to a chat's message history.

    Args:
        chat_id (str): The ID of the chat.
        message (dict): A message dict with 'role' and 'content'.

    Returns:
        int: The number of documents updated (should be 1).
    """
    try:
        if not ObjectId.is_valid(chat_id):
            raise ValueError(f"'{chat_id}' is not a valid ObjectId.")
        update_result = chat_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return update_result.modified_count
    except Exception as e:
        raise Exception(f"Failed to add message to chat: {e}")


def delete_chat(chat_id):
    """
    Deletes a chat by its ID.

    Args:
        chat_id (str): The ID of the chat.

    Returns:
        int: The number of documents deleted (should be 1).
    """
    try:
        if not ObjectId.is_valid(chat_id):
            raise ValueError(f"'{chat_id}' is not a valid ObjectId.")
        delete_result = chat_collection.delete_one({"_id": ObjectId(chat_id)})
        return delete_result.deleted_count
    except Exception as e:
        raise Exception(f"Failed to delete chat: {e}")
