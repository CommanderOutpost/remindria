from datetime import datetime
from bson import ObjectId
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
from app.models.schedule_model import (
    create_schedule,
    find_schedule_by_name_and_datetime,
    update_schedule,
    find_schedules_by_user_id,
    delete_schedule,
)
from app.utils.helper import (
    format_schedule_human_readable,
    extract_speak_block,
)
from app.ai.caller import (
    generate_action_response,
    get_ai_response,
    summarize_with_ai,
    generate_chat_title,
    parse_natural_language_instructions,
)
from bson.errors import InvalidId
from app.models.assistant_model import find_assistant_by_id


def create_new_chat_with_system_prompt(
    user_id, user, assistant_id, conversation_type="chat"
):
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

    mandatory_rules = (
        f"Here are the user’s relevant schedules:\n\n{schedules_readable}\n\n"
        f"Here’s a summary of new announcements:\n\n{summary_not_seen}\n\n"
        f"Here’s a summary of older announcements:\n\n{summary_seen}\n\n"
        "Always ask questions in your way if details are missing.\n"
        "If the user asks to create a schedule, ask for all info needed to create it. Ask for only start date and time, end date and time and name for now. \n"
        "If the user asks to update a schedule, ask for the schedule they want to update and the information they want to change. \n"
        "If the user asks to delete a schedule, ask for the schedule they want to delete. \n"
        "If the user does not specify a date, assume they mean today. \n"
        "If the user asks for more than one action to be done at the same time. Make sure you get all the info needed for all tasks.\n"
        "After finding out what the user wants to create, update or delete and with what, ALWAYS ALWAYS ask for confirmation. "
        "Today's date is " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "."
        "Use the current date and time as a reference for the user's schedules, requests and announcements."
    )

    call_rules = (
        "You are speaking with the user on a phone call."
        "Example of what you should produce: <prosody pitch='+10%' rate='fast'>“Hey there!”</prosody> or <prosody pitch='+15%' rate='fast'>“Sure thing!”</prosody>"
        "You respond verbally, as though you're talking in real time, and you must produce SSML markup for speech synthesis. "
        "IMPORTANT RULES:\n"
        "1) **All** your output must be valid SSML within a single <speak>...</speak> block.\n"
        "2) Do **not** provide code fences (```).\n"
        "3) You can use the following SSML features for realism:\n"
        "   - <prosody> for pitch/rate changes\n"
        "   - <break> to insert natural pauses\n"
        "   - <emphasis> to highlight key words\n"
        "   - volume/pitch variations for emotional effect\n"
        "Again, respond **only** with SSML in a <speak>...</speak> block. No extraneous text. "
        "4) Assume the user can handle the SSML output directly in a TTS engine.\n\n"
        "5) No disclaimers, no code blocks—only SSML.\n"
    )

    assistant = find_assistant_by_id(assistant_id)
    assistant_name = assistant.get("name", "Assistant")
    assistant_personality = assistant.get("personality")
    assistant_language = assistant.get("language")

    if conversation_type == "call":
        system_prompt = (
            f"You are {assistant_name}. You speak only {assistant_language}. Your personality is {assistant_personality}. \n"
            f"{call_rules}"
            f"{mandatory_rules}"
        )

    else:
        system_prompt = {
            f"You are {assistant_name}. You speak only {assistant_language}. Your personality is {assistant_personality}. \n"
            f"{mandatory_rules}"
        }

    chat_title = "Chat with Remindria"

    # Start conversation with system message
    conversation_history = [{"role": "system", "content": system_prompt}]

    # Create the chat in the DB
    chat_data = {
        "user_id": user_id,
        "messages": conversation_history,
        "title": chat_title,
        "conversation_type": conversation_type,
    }

    new_chat_id = create_chat(chat_data)
    return conversation_history, chat_title, new_chat_id, schedules


def get_or_create_chat(user_id, data, assistant_id, conversation_type="chat"):
    """
    If chat_id is provided, fetch that chat from DB.
    If not, create a new chat with system prompt.
    Returns: chat_doc, conversation_history, chat_title, chat_id
    """
    chat_id = data.get("chat_id")
    user = find_user_by_id(user_id)
    if not user:
        return None, None, None, None, None

    if chat_id:
        chat = find_chat_by_id(chat_id)
        if not chat or str(chat["user_id"]) != user_id:
            return None, None, None, None, None
        return chat, chat["messages"], chat["title"], chat_id, None

    # Otherwise create new
    conversation_history, chat_title, new_id, schedules = (
        create_new_chat_with_system_prompt(
            user_id, user, assistant_id, conversation_type
        )
    )
    return {}, conversation_history, chat_title, new_id, schedules


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


def actually_create_schedule(
    schedule_data, user_id, conversation_history=None, conversation_type="chat"
):
    """
    Creates schedule in DB and returns the AI-generated success/fail message.
    schedule_data: { "title": str, "start_time": datetime, "end_time": datetime, "image": str }
    """
    try:
        title = schedule_data.get("title", "Untitled")
        start_dt = schedule_data.get("start_time", datetime.now())
        end_dt = schedule_data.get("end_time")
        image = schedule_data.get("image")

        payload = {
            "user_id": user_id,
            "reminder_message": title,
            "schedule_date": start_dt,
            "schedule_end_date": end_dt,
            "image": image,
            "recurrence": None,
            "status": "Pending",
        }

        created_id = create_schedule(payload)
        # If we got here, success
        schedule_info = {
            "title": title,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "created_id": created_id,
        }
        # We call the LLM to produce a success message:
        final_msg = generate_action_response(
            action_type="create",
            success=True,
            schedule_info=schedule_info,
            conversation_history=conversation_history or [],
            conversation_type=conversation_type,
        )
        return created_id, final_msg

    except Exception as e:
        # If we got here, something failed
        schedule_info = {
            "error_details": str(e),
            "title": schedule_data.get("title", "Untitled"),
        }
        final_msg = generate_action_response(
            action_type="create",
            success=False,
            schedule_info=schedule_info,
            conversation_history=conversation_history or [],
            conversation_type=conversation_type,
        )
        return None, final_msg


def actually_update_schedule(
    schedule_data, user_id, conversation_history=None, conversation_type="chat"
):
    """
    Example schedule_data structure:
    {
      "schedule_identifier": "Doctor Appointment",
      "existing_start_time": <datetime>,
      "new_title": "Doc Appt Updated",
      "new_start_time": <datetime or None>,
      "new_end_time": <datetime or None>
    }
    """
    try:
        identifier = schedule_data["schedule_identifier"]
        existing_start_dt = schedule_data.get("existing_start_time")
        new_title = schedule_data.get("new_title")
        new_start = schedule_data.get("new_start_time")
        new_end = schedule_data.get("new_end_time")

        schedule_doc = find_schedule_by_name_and_datetime(
            user_id, identifier, existing_start_dt
        )
        if not schedule_doc:
            raise ValueError(
                f"Could not find a schedule named '{identifier}' at {existing_start_dt} to update."
            )

        schedule_id = str(schedule_doc["_id"])

        updates = {}
        if new_title:
            updates["reminder_message"] = new_title
        if new_start:
            updates["schedule_date"] = new_start
        if new_end:
            updates["schedule_end_date"] = new_end

        if not updates:
            raise ValueError("No new changes provided.")

        count = update_schedule(schedule_id, updates)
        if count == 0:
            raise ValueError(
                f"Failed to update schedule '{identifier}' at {existing_start_dt}."
            )

        schedule_info = {
            "identifier": identifier,
            "original_time": (
                existing_start_dt.isoformat() if existing_start_dt else None
            ),
            "updates": updates,
        }
        final_msg = generate_action_response(
            action_type="update",
            success=True,
            schedule_info=schedule_info,
            conversation_type=conversation_type,
            conversation_history=conversation_history or [],
        )
        return final_msg

    except Exception as e:
        schedule_info = {"error_details": str(e), "schedule_data": schedule_data}
        final_msg = generate_action_response(
            action_type="update",
            success=False,
            schedule_info=schedule_info,
            conversation_history=conversation_history or [],
            conversation_type=conversation_type,
        )
        return final_msg


def actually_delete_schedule(
    schedule_data, user_id, conversation_history=None, conversation_type="chat"
):
    """
    Example schedule_data structure:
    {
      "schedule_identifier": "Doctor Appointment",
      "existing_start_time": <datetime>
    }
    """
    try:
        identifier = schedule_data["schedule_identifier"]
        existing_start_dt = schedule_data.get("existing_start_time")

        schedule_doc = find_schedule_by_name_and_datetime(
            user_id, identifier, existing_start_dt
        )
        if not schedule_doc:
            raise ValueError(
                f"Could not find a schedule named '{identifier}' at {existing_start_dt} to delete."
            )

        schedule_id = str(schedule_doc["_id"])
        deleted_count = delete_schedule(schedule_id)
        if deleted_count == 0:
            raise ValueError(
                f"Failed to delete schedule '{identifier}' at {existing_start_dt}."
            )

        schedule_info = {
            "identifier": identifier,
            "original_time": (
                existing_start_dt.isoformat() if existing_start_dt else None
            ),
        }
        final_msg = generate_action_response(
            action_type="delete",
            success=True,
            schedule_info=schedule_info,
            conversation_history=conversation_history or [],
            conversation_type=conversation_type,
        )
        return final_msg

    except Exception as e:
        schedule_info = {"error_details": str(e), "schedule_data": schedule_data}
        final_msg = generate_action_response(
            action_type="delete",
            success=False,
            schedule_info=schedule_info,
            conversation_history=conversation_history or [],
            conversation_type=conversation_type,
        )
        return final_msg


@jwt_required()
def chat():
    """
    Main chat endpoint.
    1. Load or create the chat doc
    2. Append user message
    3. Parse entire conversation to see if user wants to add/update/delete schedules
    4. If yes, handle each schedule action in the array
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

        assistant_id = data.get("assistant_id")
        if not assistant_id:
            return jsonify({"error": "Assistant ID is required"}), 400

        conversation_type = data.get("type", "chat")

        # 1) Load or create chat
        chat_doc, conversation_history, chat_title, chat_id, schedules = (
            get_or_create_chat(user_id, data, assistant_id, conversation_type)
        )
        if conversation_history is None:
            return jsonify({"error": "Chat not found or unauthorized"}), 404

        # 2) Append user message
        append_user_message(chat_id, conversation_history, prompt)

        # 3) Let the LLM parse the entire conversation to see if there's a schedule request
        #    Now parse_natural_language_instructions returns a LIST of actions or None
        intent_result = parse_natural_language_instructions(
            conversation_history, schedules
        )

        # 4) Handle schedule actions if they exist
        if intent_result:  # This is now a list of action dicts or None
            all_responses = []  # We'll collect each action's final message here

            # Loop through each action
            for action_dict in intent_result:
                intent = action_dict["intent"]

                if intent == "add_schedule":
                    # Gather the data
                    schedule_title = action_dict["schedule_title"]
                    start_dt = action_dict["start_time"]
                    end_dt = action_dict["end_time"]
                    image = action_dict.get("image")

                    if schedule_title and start_dt:
                        created_id, success_msg = actually_create_schedule(
                            {
                                "title": schedule_title,
                                "start_time": start_dt,
                                "end_time": end_dt,
                                "image": image,
                            },
                            user_id,
                            conversation_history,
                            conversation_type,
                        )
                        # Add assistant message with success/fail
                        ai_msg = {"role": "assistant", "content": success_msg}
                        add_message_to_chat(chat_id, ai_msg)
                        conversation_history.append(ai_msg)
                        all_responses.append(success_msg)
                    else:
                        # The LLM said "add_schedule" but didn't provide enough info
                        reply = (
                            "I see you're trying to schedule something, but "
                            "I'm missing details. Could you clarify the date/time and name?"
                        )
                        ai_msg = {"role": "assistant", "content": reply}
                        add_message_to_chat(chat_id, ai_msg)
                        conversation_history.append(ai_msg)
                        all_responses.append(reply)

                elif intent == "update_schedule":
                    update_msg = actually_update_schedule(
                        action_dict, user_id, conversation_history, conversation_type
                    )
                    ai_msg = {"role": "assistant", "content": update_msg}
                    add_message_to_chat(chat_id, ai_msg)
                    conversation_history.append(ai_msg)
                    all_responses.append(update_msg)

                elif intent == "delete_schedule":
                    msg = actually_delete_schedule(
                        action_dict, user_id, conversation_history, conversation_type
                    )
                    ai_msg = {"role": "assistant", "content": msg}
                    add_message_to_chat(chat_id, ai_msg)
                    conversation_history.append(ai_msg)
                    all_responses.append(msg)

                else:
                    # If we get here, it's an unrecognized intent
                    # (though parse_natural_language_instructions should have caught that)
                    pass

            # After processing all actions, return a combined response or last response
            combined_response = "\n".join(all_responses)
            return jsonify({"chat_id": chat_id, "response": combined_response}), 200

        # 5) Normal LLM flow if no schedule actions recognized
        maybe_proactive_trimming(chat_id, conversation_history)
        ai_response = get_ai_response(prompt, conversation_history)

        if conversation_type == "call":
            cleaned_response = extract_speak_block(ai_response)
            if not cleaned_response:
                # fallback if no <speak> found
                cleaned_response = ai_response
            final_ai_msg = cleaned_response
        else:
            # normal chat, no SSML cleaning
            final_ai_msg = ai_response

        # 6) Append AI message
        ai_msg = {"role": "assistant", "content": final_ai_msg}
        add_message_to_chat(chat_id, ai_msg)
        conversation_history.append(ai_msg)

        return jsonify({"chat_id": chat_id, "response": final_ai_msg}), 200

    except ValueError as e:
        print(e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(e)
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

        # Validate chat_id
        if not ObjectId.is_valid(chat_id):
            return jsonify({"error": "'chat_id' is not a valid ObjectId"}), 400

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

    except InvalidId:
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400

    except Exception as e:
        print(e)
        return (
            jsonify({"error": f"An unexpected error occurred. {e}"}),
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

        # Validate chat_id
        if not ObjectId.is_valid(chat_id):
            return jsonify({"error": "'chat_id' is not a valid ObjectId"}), 400

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

    except InvalidId:
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400

    except Exception:
        return (
            jsonify({"error": "An unexpected error occurred. Please try again later."}),
            500,
        )
