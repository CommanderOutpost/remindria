from flask import Blueprint
from app.views.other_view import (
    delete_other,
    sync_google_announcements_to_others,
    get_all_others
)

# Create a blueprint for other routes
other_routes = Blueprint("other", __name__)

# Assign controller functions to routes
other_routes.add_url_rule("/", view_func=get_all_others, methods=["GET"])  # Get all others
other_routes.add_url_rule("/sync/google/classroom", view_func=sync_google_announcements_to_others, methods=["POST"])  # Sync Google Classroom announcements
other_routes.add_url_rule("<other_id>", view_func=delete_other, methods=["DELETE"])  # Delete an other