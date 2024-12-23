from flask import Blueprint
from app.views.token_view import (
    add_token,
    get_all_tokens,
    get_token,
    add_google_access_and_refresh_token,
    refresh_google_access_token_view,
    delete_token,
)

# Create a blueprint for token routes
token_routes = Blueprint("token", __name__)

# General route for adding Google service tokens
token_routes.add_url_rule(
    "/auth/google/<service_name>",
    view_func=add_google_access_and_refresh_token,
    methods=["POST"],
)

# General route for refreshing Google service tokens
token_routes.add_url_rule(
    "/auth/google/<service_name>/refresh",
    view_func=refresh_google_access_token_view,
    methods=["POST"],
)

# Other routes remain the same
token_routes.add_url_rule("/", view_func=add_token, methods=["POST"])  # Create a token
token_routes.add_url_rule("/", view_func=get_all_tokens, methods=["GET"])  # Get tokens
token_routes.add_url_rule(
    "/<service_name>", view_func=get_token, methods=["GET"]
)  # Get a token based on the service name
token_routes.add_url_rule(
    "/<service_name>", view_func=delete_token, methods=["DELETE"]
)  # Delete a token based on the service name
