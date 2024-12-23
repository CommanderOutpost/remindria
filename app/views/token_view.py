from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.errors import InvalidId
from app.scheduler.google.authentication import (
    exchange_auth_code_with_google,
    refresh_google_access_token,
)
from config import config

from app.models.token_model import (
    create_token,
    find_token_by_user_and_service,
    find_tokens_by_user,
    update_token,
    delete_token as delete_token_model,
)


@jwt_required()
def add_token():
    """
    Handles the addition of a new token for a service. Requires JWT authentication.

    Request JSON Body:
        {
            "service_name": "string",  # Name of the service (required, e.g., "google")
            "access_token": "string",  # Access token for the service (required)
            "refresh_token": "string",  # Refresh token for the service (optional)
            "token_expiry": "string"  # ISO 8601 format datetime (optional)
        }

    Returns:
        JSON Response:
            - Success: {"message": "Token added successfully", "token_id": "string"}
            - Success: {"message": "Token updated successfully"}
            - Error: {"error": "string"}
    """
    try:
        # Parse request JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is missing"}), 400

        print(data)

        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Validate required fields
        required_fields = ["service_name", "access_token"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"'{field}' is a required field"}), 400

        # Validate token_expiry if provided
        token_expiry = None
        if "token_expiry" in data:
            try:
                token_expiry = datetime.fromisoformat(data["token_expiry"])
            except ValueError:
                return (
                    jsonify(
                        {
                            "error": "'token_expiry' must be a valid ISO 8601 datetime string"
                        }
                    ),
                    400,
                )

        # Check if a token already exists for this user and service
        existing_token = find_token_by_user_and_service(user_id, data["service_name"])

        token_data = {
            "user_id": user_id,  # Use the authenticated user's ID
            "service_name": data["service_name"],
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", None),  # Optional field
            "token_expiry": token_expiry,  # Optional field
        }

        if existing_token:
            # Prepare updates by excluding 'user_id' and 'service_name'
            updates = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "token_expiry": token_expiry,
            }

            update_count = update_token(user_id, data["service_name"], updates)
            if update_count == 0:
                return jsonify({"error": "Failed to update existing token"}), 500
            return jsonify({"message": "Token updated successfully"}), 200

        # Add the token
        token_id = create_token(token_data)
        return (
            jsonify(
                {
                    "message": "Token added successfully",
                    "token_id": str(token_id),
                }
            ),
            201,
        )
    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def get_token(service_name):
    """
    Handles the retrieval of a token for a service. Requires JWT authentication.

    Args:
        service_name (str): The name of the service (e.g., "google").

    Returns:
        JSON Response:
            - Success: {"access_token": "string", "refresh_token": "string", "token_expiry": "string"}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Find the token for the user and service
        token = find_token_by_user_and_service(user_id, service_name)
        if not token:
            return jsonify({"error": "Token not found"}), 404

        # Prepare the response
        token_data = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token", None),
            "token_expiry": token.get("token_expiry", None),
        }

        return jsonify(token_data)

    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def get_all_tokens():
    """
    Handles the retrieval of all tokens for the current user. Requires JWT authentication.

    Returns:
        JSON Response:
            - Success: [{"service_name": "string", "access_token": "string", "refresh_token": "string", "token_expiry": "string"}]
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Find all tokens for the user
        tokens = find_tokens_by_user(user_id)
        if not tokens:
            return jsonify([])

        # Prepare the response
        token_data = [
            {
                "service_name": token["service_name"],
                "access_token": token["access_token"],
                "refresh_token": token.get("refresh_token", None),
                "token_expiry": token.get("token_expiry", None),
            }
            for token in tokens
        ]

        return jsonify(token_data)

    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def delete_token(service_name):
    """
    Deletes a token for the specified service. Requires JWT authentication.

    Args:
        service_name (str): The name of the service (e.g., "google_classroom").

    Returns:
        JSON Response:
            - Success: {"message": "Token deleted successfully"}
            - Error: {"error": "Token not found"}
            - Error: {"error": "string"}
    """
    try:
        # Get the current user's ID from the JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Delete token for the user and service
        deleted_count = delete_token_model(user_id, service_name)
        if deleted_count == 0:
            return jsonify({"error": "Token not found"}), 404

        return jsonify({"message": "Token deleted successfully"}), 200

    except InvalidId:
        return jsonify({"error": "Invalid user ID in JWT"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def add_google_access_and_refresh_token(service_name):
    """
    Adds a Google access and refresh token to the database for a specified Google service.

    Args:
        service_name (str): The name of the Google service (e.g., "google_classroom", "google_calendar").

    Request JSON Body:
        {
            "code": "string",  # Authorization code from Google
            "scopes": "string"  # List of scopes to request separated by spaces
        }

    Returns:
        JSON Response:
            - Success: {"message": "Token added successfully"}
            - Error: {"error": "string"}
    """
    if service_name != "google_classroom" and service_name != "google_calendar":
        return jsonify({"error": "Invalid service name"}), 400

    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({"error": "Unauthorized access"}), 401

    # Parse request JSON
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is missing"}), 400

    # Get the authorization code and scopes from the request
    auth_code = data.get("code")
    if not auth_code:
        return jsonify({"error": "Authorization code is required"}), 400

    # scopes = data.get("scopes")
    # if not auth_code or not scopes:
    #     return jsonify({"error": "Authorization code and scopes are required"}), 400

    # Convert scopes string to a list
    # scopes = scopes.split(" ")

    # Google OAuth 2.0 client ID and client secret
    client_id = config.GOOGLE_CLIENT_ID
    client_secret = config.GOOGLE_CLIENT_SECRET
    redirect_uri = (
        "http://127.0.0.1:5000"  # Ensure this matches your OAuth 2.0 settings
    )

    try:
        # Exchange the authorization code for tokens
        tokens = exchange_auth_code_with_google(
            auth_code, client_id, client_secret, redirect_uri
        )

        # Prepare token data
        token_data = {
            "user_id": user_id,
            "service_name": service_name,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_expiry": tokens["expiry"],
        }

        # Check if token already exists
        existing_token = find_token_by_user_and_service(user_id, service_name)
        if existing_token:
            # Prepare updates by excluding 'user_id' and 'service_name'
            updates = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "token_expiry": tokens["expiry"],
            }

            modified_count = update_token(user_id, service_name, updates)
            if modified_count == 0:
                return jsonify({"error": "Failed to update token"}), 500
            return (
                jsonify(
                    {
                        "message": "Token updated successfully",
                        "access_token": tokens["access_token"],
                    }
                ),
                200,
            )

        # Create new token
        token_id = create_token(token_data)
        return (
            jsonify(
                {
                    "message": "Token added successfully",
                    "access_token": tokens["access_token"],
                }
            ),
            201,
        )


    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@jwt_required()
def refresh_google_access_token_view(service_name):
    """
    Refreshes the Google access token for the specified service for the authenticated user.

    Args:
        service_name (str): The name of the Google service (e.g., "google_classroom", "google_calendar").

    Returns:
        JSON Response:
            - Success: {"message": "Access token refreshed successfully"}
            - Error: {"error": "string"}
    """
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Unauthorized access"}), 401

        # Retrieve existing token
        token = find_token_by_user_and_service(user_id, service_name)
        if not token:
            return jsonify({"error": f"{service_name} token not found"}), 404

        refresh_token = token.get("refresh_token")
        if not refresh_token:
            return jsonify({"error": "No refresh token available"}), 400

        # Refresh the token
        client_id = config.GOOGLE_CLIENT_ID
        client_secret = config.GOOGLE_CLIENT_SECRET
        new_tokens = refresh_google_access_token(
            refresh_token, client_id, client_secret
        )

        # Update the token in the database
        update_token(
            user_id=user_id,
            service_name=service_name,
            updates={
                "access_token": new_tokens["access_token"],
                "token_expiry": new_tokens["expiry"],
            },
        )

        return (
            jsonify(
                {
                    "message": "Access token refreshed successfully",
                    "access_token": new_tokens["access_token"],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
