# app/views/chat_view.py

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user_model import find_user_by_id
from app.models.schedule_model import find_schedules_by_user_id
from app.utils.helper import format_schedule_human_readable
from app.caller.ai import get_ai_response
from app.models.chat_model import (
    create_chat,
    find_chat_by_id,
    find_chats_by_user_id,
    add_message_to_chat,
    delete_chat,
)
from datetime import datetime


@jwt_required()
def chat():
    """
    Handles the conversation with the AI assistant.
    """
    try:
        # Get user ID from JWT
        user_id = get_jwt_identity()

        # Get user info
        user = find_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get the prompt from the request
        data = request.get_json()
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Get or create a chat session
        chat_id = data.get("chat_id")
        if chat_id:
            # Fetch existing chat
            chat = find_chat_by_id(chat_id)
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            if str(chat["user_id"]) != user_id:
                return jsonify({"error": "Unauthorized access to chat"}), 403
            conversation_history = chat["messages"]
        else:
            # Create a new chat
            # Get user's schedules
            schedules = find_schedules_by_user_id(user_id)
            schedules_readable = format_schedule_human_readable(
                {"schedules": schedules}
            )

            system_prompt = f"""You are a scheduling assistant called Remindria. Your job is to call people and tell them about their upcoming schedules.
            The current user is {user['username']} who has the following schedules:
            {schedules_readable}
            The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. You will greet the user and, after they respond, tell them about their schedules.
            if the prompt is just 'start', then it's you who's starting the conversation."""

            conversation_history = [{"role": "system", "content": system_prompt}]
            chat_data = {"user_id": user_id, "messages": conversation_history}
            chat_id = create_chat(chat_data)

        # Add user message to conversation history
        user_message = {"role": "user", "content": prompt}
        add_message_to_chat(chat_id, user_message)
        conversation_history.append(user_message)

        # Get AI response
        ai_response = get_ai_response(prompt, conversation_history)

        # Add AI message to conversation history
        ai_message = {"role": "assistant", "content": ai_response}
        add_message_to_chat(chat_id, ai_message)
        conversation_history.append(ai_message)

        # Return AI response along with chat_id
        return jsonify({"chat_id": chat_id, "response": ai_response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jwt_required()
def get_chats():
    """
    Retrieves all chats for the authenticated user.
    """
    try:
        user_id = get_jwt_identity()
        chats = find_chats_by_user_id(user_id)
        # Serialize ObjectId fields
        chats_serialized = [
            {
                **chat,
                "_id": str(chat["_id"]),
                "user_id": str(chat["user_id"]),
            }
            for chat in chats
        ]
        return jsonify({"chats": chats_serialized}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jwt_required()
def get_chat_by_id(chat_id):
    """
    Retrieves a specific chat by its ID for the authenticated user.
    """
    try:
        user_id = get_jwt_identity()
        chat = find_chat_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        if str(chat["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized access to chat"}), 403
        # Serialize ObjectId fields
        chat_serialized = {
            **chat,
            "_id": str(chat["_id"]),
            "user_id": str(chat["user_id"]),
        }
        return jsonify({"chat": chat_serialized}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jwt_required()
def delete_chat_by_id(chat_id):
    """
    Deletes a specific chat by its ID for the authenticated user.
    """
    try:
        user_id = get_jwt_identity()
        chat = find_chat_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        if str(chat["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized access to chat"}), 403
        deleted_count = delete_chat(chat_id)
        if deleted_count == 0:
            return jsonify({"error": "Failed to delete chat"}), 500
        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
