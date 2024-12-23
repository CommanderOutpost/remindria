from flask import Blueprint
from app.views.auth_view import signup, login, get_user

# Create a blueprint for authentication routes
auth_routes = Blueprint("auth", __name__)

# Assign controller functions to routes
auth_routes.add_url_rule("/signup", view_func=signup, methods=["POST"])
auth_routes.add_url_rule("/login", view_func=login, methods=["POST"])
auth_routes.add_url_rule("/user", view_func=get_user, methods=["GET"])
