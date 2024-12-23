# app/views/chat_view.py

from datetime import datetime, timezone
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.user_model import find_user_by_id
from app.models.chat_model import create_chat, find_chat_by_id, add_message_to_chat
from app.views.schedule_view import get_30_day_schedules_for_user
from app.views.other_view import fetch_and_summarize_others
from app.utils.helper import format_schedule_human_readable
from app.models.chat_model import (
    create_chat,
    find_chat_by_id,
    add_message_to_chat,
    store_summary_in_chat,
    delete_chat,
    find_chats_by_user_id_after_date,
    find_chats_by_user_id,
)
from app.ai.caller import (
    get_ai_response,
    summarize_with_ai,
    conversation_token_count,
    generate_chat_title,
)


@jwt_required()
def chat():
    """
    Main chat endpoint. Either continues an existing chat or starts a new one,
    then proactively trims older messages if the user+assistant messages exceed
    some threshold, storing a summary in the chat doc.
    """
    try:
        # ----------------------
        # 1) Basic Setup
        # ----------------------
        user_id = get_jwt_identity()
        user = find_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        chat_id = data.get("chat_id")

        # ----------------------
        # 2) Existing Chat or New?
        # ----------------------
        if chat_id:
            chat = find_chat_by_id(chat_id)
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            if str(chat["user_id"]) != user_id:
                return jsonify({"error": "Unauthorized access to chat"}), 403

            conversation_history = chat["messages"]
            chat_title = chat["title"]
        else:
            # Create a new chat with system prompts
            # a) Schedules
            schedules = get_30_day_schedules_for_user(user_id)
            if schedules:
                schedules_readable = format_schedule_human_readable(
                    {"schedules": schedules}
                )
            else:
                schedules_readable = (
                    "No tasks or reminders for the past or upcoming 30 days."
                )

            # b) Summarize 'others'
            summary_not_seen, summary_seen = fetch_and_summarize_others(user_id)

            # c) Build system prompt
            system_prompt = (
                "You’re Remindria, a friendly buddy who helps users manage their schedules. "
                "You talk in a casual, approachable style, like you’ve known them for years. "
                "You focus on reminders and tasks from 30 days before and after today—stuff older than that, "
                "you can’t really remember. "
                f"Here are the user’s relevant schedules:\n\n{schedules_readable}\n\n"
                f"Here’s a summary of new announcements (not seen till now):\n\n{summary_not_seen}\n\n"
                f"Here’s a summary of older announcements the user already saw:\n\n{summary_seen}\n\n"
                "Greet the user warmly and talk about their current tasks and announcements. "
                "If they ask about other topics, you can chat briefly but keep the main focus on scheduling. "
                "Keep the vibe casual, friendly, and helpful."
                "Do not assume the user has nothing to do if it's not specified in their schedule."
                "Don't add any text formatting like markdown, just plain text."
                "Today's date is " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "."
            )

            # d) Generate a chat title using AI
            chat_title = generate_chat_title(
                user_info=user,
                schedules_readable=schedules_readable,
                not_seen_others_readable=summary_not_seen,
                seen_others_readable=summary_seen,
            )

            # e) Start conversation
            conversation_history = [{"role": "system", "content": system_prompt}]
            chat_data = {
                "user_id": user_id,
                "messages": conversation_history,
                "title": chat_title,
            }
            chat_id = create_chat(chat_data)

        # ----------------------
        # 3) Append User Message
        # ----------------------
        user_message = {"role": "user", "content": prompt}
        add_message_to_chat(chat_id, user_message)
        conversation_history.append(user_message)

        # ----------------------
        # 4) Proactive Trimming
        # ----------------------
        # Let's say we only want to keep the last 8 user+assistant messages in memory.
        MAX_RECENT = 8

        # Split system vs user/assistant messages
        system_msgs = [m for m in conversation_history if m["role"] == "system"]
        user_assistant_msgs = [
            m for m in conversation_history if m["role"] in ["user", "assistant"]
        ]

        if len(user_assistant_msgs) > MAX_RECENT:
            # a) We have older messages to summarize
            older_count = len(user_assistant_msgs) - MAX_RECENT
            older_chunk = user_assistant_msgs[:older_count]  # older messages
            recent_chunk = user_assistant_msgs[older_count:]  # last 8

            # b) Summarize that older chunk
            summary_text = summarize_with_ai(older_chunk)

            # c) Fetch existing summary
            current_chat_doc = find_chat_by_id(chat_id)
            existing_summary = current_chat_doc.get("summary_so_far") or ""

            # d) Combine existing summary + new summary chunk
            combined_summary = (
                existing_summary + "\n\n" + summary_text
                if existing_summary
                else summary_text
            )

            # e) Store combined summary in the chat doc
            store_summary_in_chat(chat_id, combined_summary)

            # f) Rebuild conversation_history with system messages + last 8
            conversation_history.clear()
            conversation_history.extend(system_msgs)
            conversation_history.extend(recent_chunk)

        # ----------------------
        # 5) Get AI Response
        # ----------------------
        # Now our conversation is short + we can call the AI
        ai_response = get_ai_response(prompt, conversation_history)

        # ----------------------
        # 6) Append AI Message
        # ----------------------
        ai_message = {"role": "assistant", "content": ai_response}
        add_message_to_chat(chat_id, ai_message)
        conversation_history.append(ai_message)

        return (
            jsonify({"chat_id": chat_id, "response": ai_response, "title": chat_title}),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jwt_required()
def get_chats():
    """
    Retrieves all chats for the authenticated user.

    Returns:
        Response (JSON):
            - 200: On success, returns a list of chats.
            - 401: If the user is not authenticated.
            - 500: If an unexpected error occurs.
    """
    try:
        # Get the authenticated user's ID
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Retrieve chats for the user
        chats = find_chats_by_user_id(user_id)
        if chats is None:
            return jsonify({"error": "No chats found for the user"}), 404

        # Serialize ObjectId fields for JSON
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
        return (
            jsonify({"error": "An unexpected error occurred. Please try again later."}),
            500,
        )


@jwt_required()
def get_chat_by_id(chat_id):
    """
    Retrieves a specific chat by its ID for the authenticated user.

    Parameters:
        chat_id (str): The ID of the chat to retrieve.

    Returns:
        Response (JSON):
            - 200: On success, returns the chat details.
            - 401: If the user is not authenticated.
            - 403: If the user does not own the chat.
            - 404: If the chat is not found.
            - 500: If an unexpected error occurs.
    """
    try:
        # Get the authenticated user's ID
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Retrieve the specific chat by ID
        chat = find_chat_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        # Check if the user owns the chat
        if str(chat["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        # Serialize ObjectId fields for JSON
        chat_serialized = {
            **chat,
            "_id": str(chat["_id"]),
            "user_id": str(chat["user_id"]),
        }

        return jsonify({"chat": chat_serialized}), 200

    except Exception as e:
        return (
            jsonify({"error": "An unexpected error occurred. Please try again later."}),
            500,
        )


@jwt_required()
def get_chats_after_datetime(date_str):
    """
    Retrieves all chats created after a specific date and time.

    Returns:
        Response (JSON):
            - 200: On success, returns a list of chats.
            - 500: If an unexpected error occurs.
    """
    try:
        # Get the authenticated user's ID
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Get the date and time from the query parameters
        if not date_str:
            return jsonify({"error": "Date is required"}), 400

        date = datetime.fromisoformat(date_str)
        if not date:
            return jsonify({"error": "Invalid date format"}), 400

        # Retrieve chats created after the given date
        chats = find_chats_by_user_id_after_date(user_id, date)
        if chats is None:
            return jsonify({"error": "No chats found after the given date"}), 404

        # Serialize ObjectId fields for JSON
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
        return (
            jsonify({"error": "An unexpected error occurred. Please try again later."}),
            500,
        )


@jwt_required()
def delete_chat_by_id(chat_id):
    """
    Deletes a specific chat by its ID for the authenticated user.

    Parameters:
        chat_id (str): The ID of the chat to delete.

    Returns:
        Response (JSON):
            - 200: On success, confirms chat deletion.
            - 401: If the user is not authenticated.
            - 403: If the user does not own the chat.
            - 404: If the chat is not found.
            - 500: If the deletion fails or an unexpected error occurs.
    """
    try:
        # Get the authenticated user's ID
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Retrieve the specific chat by ID
        chat = find_chat_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        # Check if the user owns the chat
        if str(chat["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        # Delete the chat and check the result
        deleted_count = delete_chat(chat_id)
        if deleted_count == 0:
            return jsonify({"error": "Failed to delete chat"}), 500

        return jsonify({"message": "Chat deleted successfully"}), 200

    except Exception:
        return (
            jsonify({"error": "An unexpected error occurred. Please try again later."}),
            500,
        )
