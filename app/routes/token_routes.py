from flask import Blueprint
from app.views.token_view import add_token, get_all_tokens, get_token

# Create a blueprint for token routes
token_routes = Blueprint("token", __name__)

# Assign controller functions to routes
token_routes.add_url_rule("/", view_func=add_token, methods=["POST"])  # Create a token
token_routes.add_url_rule("/", view_func=get_all_tokens, methods=["GET"])  # Get tokens
token_routes.add_url_rule("/<service_name>", view_func=get_token, methods=["GET"])  # Get a token based on the service name
