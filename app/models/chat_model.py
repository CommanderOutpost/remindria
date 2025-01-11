# app/models/chat_model.py

from db import db, get_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone

# Collection reference
chat_collection = get_collection(
    "chats",
    indexes=[
        [("user_id", 1)],  # Index on user_id for faster lookups
        [("updated_at", -1)],  # Index on updated_at for sorting
    ],
)


class ChatModel:
    """
    Represents a chat conversation between a user and the AI assistant.

    Attributes:
        user_id (ObjectId): The ID of the user who owns the chat.
        assitant_id (ObjectId): The ID of the assistant who the user is communicating with.
        messages (list): A list of messages in the conversation. Each message is a dict with 'role' and 'content'.
        created_at (datetime): Timestamp when the chat was created.
        updated_at (datetime): Timestamp when the chat was last updated.
    """

    def __init__(
        self,
        user_id,
        assistant_id,
        messages=None,
        summary_so_far=None,
        pending_schedule=None,
        pending_schedule_step=None,
        conversation_type="chat",
        created_at=None,
        updated_at=None,
    ):
        self.user_id = ObjectId(user_id)
        self.assistant_id = ObjectId(assistant_id)
        self.messages = messages or []
        self.summary_so_far = summary_so_far
        self.pending_schedule = pending_schedule or {}
        self.pending_schedule_step = pending_schedule_step or None
        self.conversation_type = conversation_type
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "assistant_id": self.assistant_id,
            "messages": self.messages,
            "summary_so_far": self.summary_so_far,
            "pending_schedule": self.pending_schedule,
            "pending_schedule_step": self.pending_schedule_step,
            "conversation_type": self.conversation_type,
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


def find_chats_by_user_id_after_date(user_id, date):
    """
    Finds all chats for a user after a given date and time.

    Args:
        user_id (str): The ID of the user.
        date (datetime): The date and time to filter chats.

    Returns:
        list: List of chat documents.
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"'{user_id}' is not a valid ObjectId.")
        chats = list(
            chat_collection.find(
                {"user_id": ObjectId(user_id), "updated_at": {"$gt": date}}
            )
        )
        return chats
    except Exception as e:
        raise Exception(f"Failed to find chats for user after date: {e}")


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


def store_summary_in_chat(chat_id, summary):
    """
    Updates the 'summary_so_far' field with the new summary,
    and also updates the 'updated_at' field.
    """
    try:
        if not ObjectId.is_valid(chat_id):
            raise ValueError(f"'{chat_id}' is not a valid ObjectId.")
        chat_collection.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$set": {
                    "summary_so_far": summary,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
    except Exception as e:
        raise Exception(f"Failed to store summary in chat: {e}")


def get_chat_schedule_state(chat_id):
    """
    Returns (pending_schedule, pending_schedule_step) from the chat doc.
    If not found, returns ({}, None).
    """
    chat = chat_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return {}, None
    return chat.get("pending_schedule", {}), chat.get("pending_schedule_step")


def update_chat_schedule_state(chat_id, pending_schedule, pending_schedule_step):
    """
    Updates the chat doc with the pending_schedule dict and step.
    """
    chat_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {
            "$set": {
                "pending_schedule": pending_schedule,
                "pending_schedule_step": pending_schedule_step,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
