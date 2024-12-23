from datetime import datetime, timezone
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.user_model import find_user_by_id
from app.models.chat_model import (
    find_chat_by_id,
    create_chat,
    add_message_to_chat,
    find_chats_by_user_id,
    find_chats_by_user_id_after_date,
    delete_chat,
    store_summary_in_chat,
)
from app.views.schedule_view import get_30_day_schedules_for_user
from app.views.other_view import fetch_and_summarize_others
from app.models.schedule_model import create_schedule
from app.utils.helper import (
    format_schedule_human_readable,
    parse_natural_language_instructions,  # We'll modify to accept conversation
)
from app.ai.caller import (
    get_ai_response,
    summarize_with_ai,
    generate_chat_title,
)


def create_new_chat_with_system_prompt(user_id, user):
    """
    Creates a new chat doc with a system prompt tailored to the user's schedule & announcements.
    Returns: (conversation_history, chat_title, new_chat_id)
    """
    # Summaries
    schedules = get_30_day_schedules_for_user(user_id)
    if schedules:
        schedules_readable = format_schedule_human_readable({"schedules": schedules})
    else:
        schedules_readable = "No tasks or reminders for the past or upcoming 30 days."

    summary_not_seen, summary_seen = fetch_and_summarize_others(user_id)

    # Build system prompt
    system_prompt = (
        "You’re Remindria, a friendly buddy who helps users manage their schedules. "
        "You talk in a casual, approachable style. Focus on tasks from 30 days before and after today. "
        f"Here are the user’s relevant schedules:\n\n{schedules_readable}\n\n"
        f"Here’s a summary of new announcements:\n\n{summary_not_seen}\n\n"
        f"Here’s a summary of older announcements:\n\n{summary_seen}\n\n"
        "Greet the user warmly and talk about their current tasks and announcements. "
        "Keep the vibe casual and helpful. "
        "If the user asks to create a schedule, ask for all info needed to create it. Ask for only date and time and name for now. "
        "Today's date is " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "."
    )

    # Generate chat title
    chat_title = generate_chat_title(
        user_info=user,
        schedules_readable=schedules_readable,
        not_seen_others_readable=summary_not_seen,
        seen_others_readable=summary_seen,
    )

    # Start conversation with system message
    conversation_history = [{"role": "system", "content": system_prompt}]

    # Create the chat in the DB
    chat_data = {
        "user_id": user_id,
        "messages": conversation_history,
        "title": chat_title,
    }
    new_chat_id = create_chat(chat_data)
    return conversation_history, chat_title, new_chat_id


def get_or_create_chat(user_id, data):
    """
    If chat_id is provided, fetch that chat from DB.
    If not, create a new chat with system prompt.
    Returns: chat_doc, conversation_history, chat_title, chat_id
    """
    chat_id = data.get("chat_id")
    user = find_user_by_id(user_id)
    if not user:
        return None, None, None, None

    if chat_id:
        chat = find_chat_by_id(chat_id)
        if not chat or str(chat["user_id"]) != user_id:
            return None, None, None, None
        return chat, chat["messages"], chat["title"], chat_id

    # Otherwise create new
    conversation_history, chat_title, new_id = create_new_chat_with_system_prompt(
        user_id, user
    )
    return {}, conversation_history, chat_title, new_id


def append_user_message(chat_id, conversation_history, user_prompt):
    """
    Appends the user's message to DB + conversation_history.
    """
    user_msg = {"role": "user", "content": user_prompt}
    add_message_to_chat(chat_id, user_msg)
    conversation_history.append(user_msg)


def maybe_proactive_trimming(chat_id, conversation_history):
    """
    If conversation is large, summarize older messages and store in DB.
    """
    MAX_RECENT = 8
    system_msgs = [m for m in conversation_history if m["role"] == "system"]
    user_assistant_msgs = [
        m for m in conversation_history if m["role"] in ["user", "assistant"]
    ]

    if len(user_assistant_msgs) > MAX_RECENT:
        older_count = len(user_assistant_msgs) - MAX_RECENT
        older_chunk = user_assistant_msgs[:older_count]
        recent_chunk = user_assistant_msgs[older_count:]

        summary_text = summarize_with_ai(older_chunk)
        existing_chat = find_chat_by_id(chat_id)
        existing_summary = existing_chat.get("summary_so_far") or ""

        combined_summary = (
            existing_summary + "\n\n" + summary_text
            if existing_summary
            else summary_text
        )
        store_summary_in_chat(chat_id, combined_summary)

        conversation_history.clear()
        conversation_history.extend(system_msgs)
        conversation_history.extend(recent_chunk)


def actually_create_schedule(schedule_data, user_id):
    """
    Creates schedule in DB and returns success message.
    schedule_data: { "title": str, "start_time": datetime, "end_time": optional }
    """
    title = schedule_data.get("title", "Untitled")
    start_dt = schedule_data.get("start_time", datetime.now())
    end_dt = schedule_data.get("end_time")

    payload = {
        "user_id": user_id,
        "reminder_message": title,
        "schedule_date": start_dt,
        "recurrence": None,
        "status": "Pending",
    }
    created_id = create_schedule(payload)
    disp_time = start_dt.strftime("%Y-%m-%d %H:%M")
    return created_id, f"Done! I've created the schedule '{title}' for {disp_time}."


@jwt_required()
def chat():
    """
    Main chat endpoint.
    1. Load or create the chat doc
    2. Append user message
    3. Parse entire conversation to see if user wants to add a schedule
    4. If yes, create schedule
    5. If no, do normal LLM flow
    6. Possibly trim older messages
    7. Return final response
    """
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        data = request.get_json()
        if not data or "prompt" not in data:
            return jsonify({"error": "Prompt is required"}), 400
        prompt = data["prompt"]

        # 1) Load or create chat
        chat_doc, conversation_history, chat_title, chat_id = get_or_create_chat(
            user_id, data
        )
        if conversation_history is None:
            return jsonify({"error": "Chat not found or unauthorized"}), 404

        # 2) Append user message
        append_user_message(chat_id, conversation_history, prompt)

        # 3) Let the LLM parse the entire conversation to see if there's a schedule request
        intent_result = parse_natural_language_instructions(conversation_history)
        # If you want, you could do: parse_natural_language_instructions(conversation_history, "Look for schedule creation")
        if intent_result and intent_result.get("intent") == "add_schedule":
            # 4) We got a schedule creation request
            # Gather the data from intent_result
            schedule_title = intent_result["schedule_title"]
            start_dt = intent_result["start_time"]
            end_dt = intent_result["end_time"]

            if schedule_title and start_dt:
                created_id, success_msg = actually_create_schedule(
                    {
                        "title": schedule_title,
                        "start_time": start_dt,
                        "end_time": end_dt,
                    },
                    user_id,
                )
                # Add assistant message with success
                ai_msg = {"role": "assistant", "content": success_msg}
                add_message_to_chat(chat_id, ai_msg)
                conversation_history.append(ai_msg)

                return jsonify({"chat_id": chat_id, "response": success_msg}), 200

            else:
                # The LLM said "add_schedule" but didn't provide a complete date/time or title
                # We'll just say we couldn't parse it fully
                reply = "I see you're trying to schedule something, but I'm missing details. Could you clarify the date/time and name?"
                ai_msg = {"role": "assistant", "content": reply}
                add_message_to_chat(chat_id, ai_msg)
                conversation_history.append(ai_msg)
                return jsonify({"chat_id": chat_id, "response": reply}), 200

        # 5) Normal LLM flow
        maybe_proactive_trimming(chat_id, conversation_history)
        ai_response = get_ai_response(prompt, conversation_history)

        # 6) Append AI message
        ai_msg = {"role": "assistant", "content": ai_response}
        add_message_to_chat(chat_id, ai_msg)
        conversation_history.append(ai_msg)

        return jsonify({"chat_id": chat_id, "response": ai_response}), 200

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
