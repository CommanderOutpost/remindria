from flask import Blueprint
from app.views.schedule_view import (
    add_schedule,
    update_schedule,
    get_schedule,
    delete_schedule,
    get_all_schedules,
)

# Create a blueprint for schedule routes
schedule_routes = Blueprint("schedule", __name__)

# Assign controller functions to routes
schedule_routes.add_url_rule("/", view_func=get_all_schedules, methods=["GET"])  # Get all schedules
schedule_routes.add_url_rule("/<id>", view_func=get_schedule, methods=["GET"])  # Get one schedule
schedule_routes.add_url_rule("/", view_func=add_schedule, methods=["POST"])  # Add a new schedule
schedule_routes.add_url_rule("/<id>", view_func=update_schedule, methods=["PUT"])  # Update a schedule
schedule_routes.add_url_rule("/<id>", view_func=delete_schedule, methods=["DELETE"])  # Delete a schedule
