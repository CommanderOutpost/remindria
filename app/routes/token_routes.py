from flask import Blueprint
from app.views.token_view import add_token, get_all_tokens, get_token, add_google_classroom_access_and_refresh_token, refresh_google_classroom_access_token, delete_token

# Create a blueprint for token routes
token_routes = Blueprint("token", __name__)

# Assign controller functions to routes
token_routes.add_url_rule("/", view_func=add_token, methods=["POST"])  # Create a token
token_routes.add_url_rule("/auth/google/classroom", view_func=add_google_classroom_access_and_refresh_token, methods=["POST"])  # Create a Google Classroom token
token_routes.add_url_rule("/auth/google/classroom/refresh", view_func=refresh_google_classroom_access_token, methods=["POST"])  # Refresh a Google Classroom token
token_routes.add_url_rule("/", view_func=get_all_tokens, methods=["GET"])  # Get tokens
token_routes.add_url_rule("/<service_name>", view_func=get_token, methods=["GET"])  # Get a token based on the service name
token_routes.add_url_rule("/<service_name>", view_func=delete_token, methods=["DELETE"])  # Delete a token based on the service name