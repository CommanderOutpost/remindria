from bson import ObjectId
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.schedule_model import (
    create_schedule,
    find_schedules_by_user_id,
    find_schedule_by_id,
    get_schedules_in_date_range,
    update_schedule as update_schedule_model,
    delete_schedule as delete_schedule_model,
)
from datetime import datetime, timezone, timedelta
from bson.errors import InvalidId

from app.models.token_model import find_token_by_user_and_service, update_token
from app.scheduler.google.authentication import refresh_google_access_token
from app.scheduler.google.calendar import get_upcoming_events
from app.scheduler.google.classroom import get_upcoming_coursework

from config import config


def get_30_day_schedules_for_user(user_id):
    """
    Retrieves schedules within ±30 days from now.
    Anything older or far in the future is excluded.
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)
    end_date = now + timedelta(days=30)

    schedules = get_schedules_in_date_range(user_id, start_date, end_date)
    return schedules


@jwt_required()
def add_schedule():
    """
    Handles the creation of a new schedule. Requires JWT authentication.

    Request JSON Body:
        {
            "reminder_message": "string",  # Reminder message (required)
            "schedule_date": "string",  # ISO 8601 format datetime (required)
            "recurrence": "string",  # Recurrence type (optional, e.g., "None", "Daily", "Weekly", "Monthly")
            "status": "string"  # Status (optional, default is "Pending")
        }

    Returns:
        JSON Response:
            - Success: {"message": "Schedule created successfully", "schedule_id": "string"}
            - Error: {"error": "string"}
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is missing"}), 400

        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Validate required fields
        required_fields = ["reminder_message", "schedule_date"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"'{field}' is a required field"}), 400

        # Validate schedule_date
        try:
            data["schedule_date"] = datetime.fromisoformat(data["schedule_date"])
        except ValueError:
            return (
                jsonify(
                    {
                        "error": "'schedule_date' must be a valid ISO 8601 datetime string"
                    }
                ),
                400,
            )

        # Prepare the schedule data
        schedule_data = {
            "user_id": user_id,  # Use the authenticated user's ID
            "reminder_message": data["reminder_message"],
            "schedule_date": data["schedule_date"],
            "recurrence": data.get("recurrence", None),  # Optional field
            "status": data.get("status", "Pending"),  # Default to "Pending"
        }

        # Create the schedule
        schedule_id = create_schedule(schedule_data)
        return (
            jsonify(
                {
                    "message": "Schedule created successfully",
                    "schedule_id": str(schedule_id),
                }
            ),
            201,
        )

    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def update_schedule(id):
    """
    Handles updating an existing schedule. Requires JWT authentication.

    Args:
        id (str): The ID of the schedule to update.

    Request JSON Body:
        {
            "updates": {  # Fields to update (at least one required)
                "reminder_message": "string",
                "schedule_date": "string",  # ISO 8601 format datetime
                "recurrence": "string",
                "status": "string"
            }
        }

    Returns:
        JSON Response:
            - Success: {"message": "Schedule updated successfully"}
            - Error: {"error": "string"}
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is missing"}), 400

        # Validate required fields
        schedule_id = id
        updates = data.get("updates")

        if not schedule_id:
            return jsonify({"error": "id required"}), 400
        if not updates or not isinstance(updates, dict):
            return jsonify({"error": "'updates' must be a non-empty dictionary"}), 400

        # Validate schedule_id
        if not ObjectId.is_valid(schedule_id):
            return jsonify({"error": "'schedule_id' is not a valid ObjectId"}), 400

        # Validate schedule_date if provided
        if "schedule_date" in updates:
            try:
                updates["schedule_date"] = datetime.fromisoformat(
                    updates["schedule_date"]
                )
            except ValueError:
                print("ValueError")
                return (
                    jsonify(
                        {
                            "error": "'schedule_date' must be a valid ISO 8601 datetime string"
                        }
                    ),
                    400,
                )

        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()

        # Perform the update
        modified_count = update_schedule_model(schedule_id, updates)

        if modified_count == 0:
            return (
                jsonify(
                    {"error": "No schedule found for the given ID or no changes made"}
                ),
                404,
            )

        return jsonify({"message": "Schedule updated successfully"}), 200

    except InvalidId:
        print("InvalidId")
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def get_schedule(id):
    """
    Retrieves a specific schedule by its ID. Requires JWT authentication.

    Args:
        id (str): The ID of the schedule to fetch.

    Returns:
        JSON Response:
            - Success: {
                  "schedule": {
                      "user_id": "string",
                      "reminder_message": "string",
                      "schedule_date": "datetime",
                      "recurrence": "string",
                      "status": "string",
                      "created_at": "datetime",
                      "updated_at": "datetime"
                  }
              }
            - Error: {"error": "string"}
    """
    try:
        # Validate id
        if not ObjectId.is_valid(id):
            return jsonify({"error": "'id' is not a valid ObjectId"}), 400

        # Fetch the schedule
        schedule = find_schedule_by_id(id)
        if not schedule:
            return jsonify({"error": "Schedule not found"}), 404

        # Ensure the schedule belongs to the current user
        user_id = get_jwt_identity()
        if str(schedule["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized to access this schedule"}), 403

        # Serialize ObjectId fields
        schedule_serialized = {
            **schedule,
            "_id": str(schedule["_id"]),
            "user_id": str(schedule["user_id"]),
        }

        return jsonify({"schedule": schedule_serialized}), 200

    except InvalidId:
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.schedule_model import find_schedules_by_user_id


@jwt_required()
def get_all_schedules():
    """
    Retrieves all schedules for the currently authenticated user. Requires JWT authentication.

    Returns:
        JSON Response:
            - Success: {
                  "schedules": [
                      {
                          "user_id": "string",
                          "reminder_message": "string",
                          "schedule_date": "datetime",
                          "recurrence": "string",
                          "status": "string",
                          "created_at": "datetime",
                          "updated_at": "datetime"
                      },
                      ...
                  ]
              }
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Fetch all schedules for the user
        schedules = find_schedules_by_user_id(user_id)
        if not schedules:
            return (
                jsonify({"schedules": []}),
                200,
            )  # Return an empty list if no schedules found

        # Convert ObjectId fields to strings
        schedules_serialized = [
            {
                **schedule,
                "_id": str(schedule["_id"]),
                "user_id": str(schedule["user_id"]),
            }
            for schedule in schedules
        ]

        return jsonify({"schedules": schedules_serialized}), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def get_recent_schedules(amount=7):
    """
    Retrieves the most recent <amount> schedules for the currently authenticated user. Requires JWT authentication.

    Request Arguments:
        - amount (int): The number of schedules to retrieve (default is 7).

        Returns:
            JSON Response:
                - Success: {
                      "schedules": [
                          {
                              "user_id": "string",
                              "reminder_message": "string",
                              "schedule_date": "datetime",
                              "recurrence": "string",
                              "status": "string",
                              "created_at": "datetime",
                              "updated_at": "datetime"
                          },
                          ...
                      ]
                  }
                - Error: {"error": "string"}
    """

    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        amount = int(amount)  # Convert to integer

        # Fetch the most recent schedules for the user
        schedules = find_schedules_by_user_id(user_id, amount)
        if not schedules:
            return (
                jsonify({"schedules": []}),
                200,
            )  # Return an empty list if no schedules found

        # Convert ObjectId fields to strings
        schedules_serialized = [
            {
                **schedule,
                "_id": str(schedule["_id"]),
                "user_id": str(schedule["user_id"]),
            }
            for schedule in schedules
        ]

        return jsonify({"schedules": schedules_serialized}), 200

    except ValueError:
        return jsonify({"error": "'amount' must be an integer"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def delete_schedule(id):
    """
    Deletes a specific schedule by its ID. Requires JWT authentication.

    Args:
        id (str): The ID of the schedule to delete.

    Returns:
        JSON Response:
            - Success: {"message": "Schedule deleted successfully"}
            - Error: {"error": "string"}
    """
    try:

        # Validate required field
        schedule_id = id
        if not schedule_id:
            return jsonify({"error": "'schedule_id' is required"}), 400

        # Validate schedule_id
        if not ObjectId.is_valid(schedule_id):
            return jsonify({"error": "'schedule_id' is not a valid ObjectId"}), 400

        # Fetch the schedule to verify ownership
        schedule = find_schedule_by_id(schedule_id)
        if not schedule:
            return jsonify({"error": "Schedule not found"}), 404

        # Ensure the schedule belongs to the current user
        user_id = get_jwt_identity()
        if str(schedule["user_id"]) != user_id:
            return jsonify({"error": "Unauthorized to delete this schedule"}), 403

        # Delete the schedule
        deleted_count = delete_schedule_model(schedule_id)
        if deleted_count == 0:
            return jsonify({"error": "Failed to delete the schedule"}), 500

        return jsonify({"message": "Schedule deleted successfully"}), 200

    except InvalidId:
        return jsonify({"error": "Invalid ObjectId for schedule_id"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def sync_google_coursework_to_schedules():
    """
    Syncs upcoming Google Classroom coursework to the schedule database for the authenticated user.

    Requires JWT authentication.

    Returns:
        JSON Response:
            - Success: {"message": "Coursework synced successfully", "new_schedules": [<schedule_ids>]}
            - No New Coursework: {"message": "No new coursework found to sync"}
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
                    "google",
                    {
                        "access_token": refreshed_token["access_token"],
                        "token_expiry": refreshed_token["expiry"].isoformat(),
                    },
                )
            except Exception as e:
                return jsonify({"error": f"Failed to refresh token: {str(e)}"}), 500

        # Fetch upcoming coursework using the valid access token
        try:
            coursework = get_upcoming_coursework(access_token)
        except Exception as e:
            return jsonify({"error": f"Failed to fetch coursework: {str(e)}"}), 500

        # Get existing schedules for the user
        existing_schedules = find_schedules_by_user_id(user_id)
        existing_reminders = {
            schedule["reminder_message"] for schedule in existing_schedules
        }

        # Add new coursework to schedules
        new_schedule_ids = []
        for work in coursework:
            reminder_message = work["reminder_message"]
            schedule_date = datetime.fromisoformat(work["due_date"])

            if reminder_message not in existing_reminders:
                # Prepare schedule data
                schedule_data = {
                    "user_id": user_id,
                    "reminder_message": reminder_message,
                    "schedule_date": schedule_date,
                    "recurrence": None,  # Coursework doesn't recur by default
                    "status": "Pending",
                }

                # Add the schedule to the database
                try:
                    schedule_id = create_schedule(schedule_data)
                    new_schedule_ids.append(schedule_id)
                except Exception as e:
                    return (
                        jsonify({"error": f"Failed to create schedule: {str(e)}"}),
                        500,
                    )

        # Return appropriate response based on whether new schedules were added
        if not new_schedule_ids:
            return jsonify({"message": "No new coursework found to sync"}), 200

        return (
            jsonify(
                {
                    "message": "Coursework synced successfully",
                    "new_schedules": new_schedule_ids,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def sync_google_calendar_to_schedules():
    """
    Syncs upcoming Google Calendar events to the schedule database for the authenticated user.

    Returns:
        JSON Response:
            - Success: {"message": "Events synced successfully", "new_schedules": [<schedule_ids>]}
            - No New Events: {"message": "No new events found to sync"}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Retrieve the token for Google Calendar
        token_data = find_token_by_user_and_service(user_id, "google_calendar")
        if not token_data:
            return jsonify({"error": "No token found for Google Calendar"}), 404

        # Check if the token is expired and refresh if necessary
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
            refreshed_token = refresh_google_access_token(
                refresh_token,
                config.GOOGLE_CLIENT_ID,
                config.GOOGLE_CLIENT_SECRET,
            )
            access_token = refreshed_token["access_token"]

            # Update the token in the database
            update_token(
                user_id,
                "google_calendar",
                {
                    "access_token": refreshed_token["access_token"],
                    "token_expiry": refreshed_token["expiry"].isoformat(),
                },
            )

        # Fetch upcoming events using the valid access token
        events = get_upcoming_events(access_token)

        # Get existing schedules for the user
        existing_schedules = find_schedules_by_user_id(user_id)
        existing_event_ids = {
            schedule.get("event_id")
            for schedule in existing_schedules
            if schedule.get("event_id")
        }

        # Add new events to schedules
        new_schedule_ids = []
        for event in events:
            event_id = event["event_id"]
            if event_id not in existing_event_ids:
                # Prepare schedule data
                schedule_data = {
                    "user_id": user_id,
                    "reminder_message": event["summary"],
                    "schedule_date": event["start_time"],
                    "recurrence": None,  # Handle recurrence if necessary
                    "status": "Pending",
                    "event_id": event_id,  # Store the event ID to prevent duplicates
                }

                # Add the schedule to the database
                try:
                    schedule_id = create_schedule(schedule_data)
                    new_schedule_ids.append(schedule_id)
                except Exception as e:
                    return (
                        jsonify({"error": f"Failed to create schedule: {str(e)}"}),
                        500,
                    )

        # Return appropriate response based on whether new schedules were added
        if not new_schedule_ids:
            return jsonify({"message": "No new events found to sync"}), 200

        return (
            jsonify(
                {
                    "message": "Events synced successfully",
                    "new_schedules": new_schedule_ids,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def get_schedules_in_date_range_view():
    """
    Retrieves schedules for the authenticated user within a specified date range.

    Query Parameters:
        - start_date (str): The start date in ISO 8601 format (e.g., "2024-01-01").
        - end_date (str): The end date in ISO 8601 format (e.g., "2024-01-30").

    Returns:
        JSON Response:
            - Success: {
                  "schedules": [
                      {
                          "_id": "string",
                          "user_id": "string",
                          "reminder_message": "string",
                          "schedule_date": "datetime",
                          "recurrence": "string",
                          "status": "string",
                          "created_at": "datetime",
                          "updated_at": "datetime",
                          "event_id": "string"  # Optional
                      },
                      ...
                  ]
              }
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Extract query parameters
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        # Validate presence of both parameters
        if not start_date_str or not end_date_str:
            return (
                jsonify(
                    {
                        "error": "'start_date' and 'end_date' query parameters are required"
                    }
                ),
                400,
            )

        # Parse the dates
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            return (
                jsonify(
                    {
                        "error": "'start_date' and 'end_date' must be valid ISO 8601 date strings"
                    }
                ),
                400,
            )

        # Ensure start_date is before end_date
        if start_date > end_date:
            return jsonify({"error": "'start_date' must be before 'end_date'"}), 400

        # Fetch schedules within the specified date range
        schedules = get_schedules_in_date_range(user_id, start_date, end_date)

        # If no schedules found, return an empty list
        if not schedules:
            return jsonify({"schedules": []}), 200

        # Serialize schedules
        schedules_serialized = [
            {
                **schedule,
                "_id": str(schedule["_id"]),
                "user_id": str(schedule["user_id"]),
                "schedule_date": schedule["schedule_date"].isoformat(),
                "created_at": schedule["created_at"].isoformat(),
                "updated_at": schedule["updated_at"].isoformat(),
                # Include 'event_id' if it exists
                **(
                    {"event_id": schedule["event_id"]} if "event_id" in schedule else {}
                ),
            }
            for schedule in schedules
        ]

        return jsonify({"schedules": schedules_serialized}), 200

    except ValueError as ve:
        return jsonify({"error": f"Validation Error: {str(ve)}"}), 400
    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
