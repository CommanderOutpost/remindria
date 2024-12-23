from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from app.models.user_model import create_user, find_user_by_id, user_collection
from flask_jwt_extended import jwt_required, get_jwt_identity


def signup():
    """
    Handles user signup by validating input, checking for existing users,
    hashing the password, and creating a new user record in the database.

    Returns:
        JSON response with a success message and HTTP 201 status code on successful signup.
        JSON response with an error message and appropriate HTTP status code on failure.
    """
    try:
        # Extract JSON data from the request
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        phone_number = data.get("phone_number")
        nationality = data.get("nationality")
        age = data.get("age")
        password = data.get("password")

        # Validate required fields
        required_fields = [
            "username",
            "email",
            "password",
            "phone_number",
            "nationality",
            "age",
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return (
                jsonify(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"}
                ),
                400,
            )

        # Check if the username or email already exists
        if user_collection.find_one(
            {"$or": [{"username": username}, {"email": email}]}
        ):
            return jsonify({"error": "Username or email already exists."}), 409

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Prepare user data for creation
        user_data = {
            "username": username,
            "email": email,
            "phone_number": phone_number,
            "nationality": nationality,
            "age": age,
            "password": hashed_password,  # Store hashed password
        }

        # Create the user in the database
        user_id = create_user(user_data)

        return (
            jsonify({"message": "User signed up successfully.", "user_id": user_id}),
            201,
        )

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": f"Failed to sign up user: {e}"}), 500


def login():
    """
    Handles user login by validating credentials and returning a JWT token.
    """
    try:
        # Extract JSON data
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        # Validate input
        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        # Find user in the database
        user = user_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Invalid email or password."}), 401

        # Verify password
        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        # Generate JWT token
        access_token = create_access_token(identity=str(user["_id"]))
        refresh_token = create_refresh_token(identity=str(user["_id"]))

        # Return token
        return (
            jsonify(
                {
                    "message": "Login successful.",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to log in: {e}"}), 500


@jwt_required()
def get_user():
    """
    Retrieves the user details for the authenticated user.

    Returns:
        JSON response with the user details on success.
        JSON response with an error message on failure.
    """
    try:
        # Get the authenticated user's ID
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Find the user by ID
        user = find_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Remove password from user data
        user.pop("password", None)

        # Serialize ObjectId field for JSON
        user_serialized = {**user, "_id": str(user["_id"])}

        return jsonify({"user": user_serialized}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve user: {e}"}), 500
