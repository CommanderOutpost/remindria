from bson import ObjectId
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.other_model import (
    create_other,
    find_others_by_user_id,
    delete_other as delete_other_model,
)
from app.models.token_model import find_token_by_user_and_service, update_token
from app.scheduler.google.authentication import refresh_google_access_token
from app.scheduler.google.classroom import get_recent_announcements
from app.models.other_model import set_seen_to_true, find_others_by_user_id
from app.ai.caller import summarize_with_ai
from datetime import datetime, timezone
from config import config
from bson.errors import InvalidId


@jwt_required()
def get_all_others():
    """
    Retrieves all `OtherModel` data for the authenticated user.

    Requires JWT authentication.

    Returns:
        JSON Response:
            - Success: {"others": [<other_data>]}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Retrieve all others for the user
        try:
            others = find_others_by_user_id(user_id)
        except Exception as e:
            return jsonify({"error": f"Failed to retrieve others: {str(e)}"}), 500

        # Serialize `ObjectId` fields to strings
        others_serialized = [
            {
                **other,
                "_id": str(other["_id"]),
                "user_id": str(other["user_id"]),
            }
            for other in others
        ]

        return jsonify({"others": others_serialized}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def sync_google_announcements_to_others():
    """
    Syncs recent Google Classroom announcements to the `OtherModel` database for the authenticated user.

    Requires JWT authentication.

    Returns:
        JSON Response:
            - Success: {"message": "Announcements synced successfully", "new_others": [<other_ids>]}
            - No New Announcements: {"message": "No new announcements found to sync"}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Retrieve the token for Google Classroom
        try:
            token_data = find_token_by_user_and_service(user_id, "google_classroom")
            if not token_data:
                return jsonify({"error": "No token found for Google Classroom"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to retrieve token: {str(e)}"}), 500

        # Check if the token is expired
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        token_expiry = token_data.get("token_expiry")

        if not access_token or not refresh_token or not token_expiry:
            return jsonify({"error": "Token data is incomplete"}), 500

        # Ensure token_expiry is a datetime object
        if isinstance(token_expiry, str):
            token_expiry = datetime.fromisoformat(token_expiry)

        # Make token_expiry offset-aware if it's naive
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)

        # Refresh the token if expired
        if token_expiry <= datetime.now(timezone.utc):
            try:
                refreshed_token = refresh_google_access_token(
                    refresh_token,
                    config.GOOGLE_CLIENT_ID,
                    config.GOOGLE_CLIENT_SECRET,
                )
                access_token = refreshed_token["access_token"]

                # Update the token in the database
                update_token(
                    user_id,
                    "google_classroom",
                    {
                        "access_token": refreshed_token["access_token"],
                        "token_expiry": refreshed_token["expiry"].isoformat(),
                    },
                )
            except Exception as e:
                return jsonify({"error": f"Failed to refresh token: {str(e)}"}), 500

        # Fetch recent announcements using the valid access token
        try:
            announcements = get_recent_announcements(access_token, minutes=4000)
        except Exception as e:
            return jsonify({"error": f"Failed to fetch announcements: {str(e)}"}), 500

        # Get existing others for the user
        existing_others = find_others_by_user_id(user_id)
        existing_content = {other["content"] for other in existing_others}

        # Add new announcements to others
        new_other_ids = []
        for announcement in announcements:
            announcement_text = (
                f"Course: {announcement['course_name']}\n"
                f"Announcement: {announcement['announcement_text']}\n"
                f"Created At: {announcement['creation_time']}"
            )

            if announcement_text not in existing_content:
                # Prepare other data
                other_data = {
                    "user_id": user_id,
                    "content": announcement_text,
                }

                # Add the other to the database
                try:
                    other_id = create_other(other_data)
                    new_other_ids.append(other_id)
                except Exception as e:
                    return (
                        jsonify({"error": f"Failed to create other: {str(e)}"}),
                        500,
                    )

        # Return appropriate response based on whether new others were added
        if not new_other_ids:
            return jsonify({"message": "No new announcements found to sync"}), 200

        return (
            jsonify(
                {
                    "message": "Announcements synced successfully",
                    "new_others": new_other_ids,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def delete_other(other_id):
    """
    Deletes an `OtherModel` entry with the specified ID.

    Args:
        other_id (str): The ID of the `OtherModel` entry to delete.

    Returns:
        JSON Response:
            - Success: {"message": "Other deleted successfully"}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401
        
        # Validate other_id
        if not ObjectId.is_valid(other_id):
            return jsonify({"error": "'other_id' is not a valid ObjectId"}), 400

        # Delete the other entry
        try:
            deleted_count = delete_other_model(other_id)
            if deleted_count == 0:
                return jsonify({"error": "Other not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete other: {str(e)}"}), 500

        return jsonify({"message": "Other deleted successfully"}), 200

    except InvalidId:
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400

    except Exception as e:
        print(e)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def fetch_and_summarize_others(user_id, char_limit=300000):
    """
    Fetches all 'others' for a user. Summarizes separately:
      1) Not-seen items
      2) Already seen items
    Only summarizes if the combined text exceeds a character count limit.
    Returns two summaries:
      - summary_not_seen
      - summary_seen
    Marks the not-seen items as seen in the database.
    If no items in a category, returns a short fallback message.
    """
    all_others = find_others_by_user_id(user_id)
    if not all_others:
        return ("No announcements found.", "No old announcements found.")

    not_seen = [o for o in all_others if not o["seen"]]
    seen = [o for o in all_others if o["seen"]]

    # ---------------------------
    # Summarize Not-Seen
    # ---------------------------
    if not_seen:
        texts_not_seen = [o["content"] for o in not_seen]
        combined_text_not_seen = "\n\n".join(texts_not_seen)

        # Only summarize if combined text exceeds the character limit
        if len(combined_text_not_seen) > char_limit:
            prompt_not_seen = (
                "Summarize the following new announcements in a friendly, casual style:\n\n"
                + combined_text_not_seen
            )
            summary_not_seen = summarize_with_ai(
                [{"role": "user", "content": prompt_not_seen}]
            )
        else:
            summary_not_seen = combined_text_not_seen

        # Now mark them as seen
        set_seen_to_true([str(o["_id"]) for o in not_seen])
    else:
        summary_not_seen = "No new announcements."

    # ---------------------------
    # Summarize Seen
    # ---------------------------
    if seen:
        texts_seen = [o["content"] for o in seen]
        combined_text_seen = "\n\n".join(texts_seen)

        # Only summarize if combined text exceeds the character limit
        if len(combined_text_seen) > char_limit:
            prompt_seen = (
                "Summarize the following older announcements (already seen by the user) in a friendly way:\n\n"
                + combined_text_seen
            )
            summary_seen = summarize_with_ai([{"role": "user", "content": prompt_seen}])
        else:
            summary_seen = combined_text_seen
    else:
        summary_seen = "No previously known announcements."

    return (summary_not_seen, summary_seen)
