from flask import Blueprint
from app.views.schedule_view import (
    add_schedule,
    update_schedule,
    get_schedule,
    delete_schedule,
    get_all_schedules,
    sync_google_coursework_to_schedules,
    sync_google_calendar_to_schedules,
    get_recent_schedules,
    get_schedules_in_date_range_view,
    delete_all_schedules,
    get_schedules_on_date_view,
)

# Create a blueprint for schedule routes
schedule_routes = Blueprint("schedule", __name__)

# Assign controller functions to routes
schedule_routes.add_url_rule(
    "/", view_func=get_all_schedules, methods=["GET"]
)  # Get all schedules
schedule_routes.add_url_rule(
    "/recent/<amount>", view_func=get_recent_schedules, methods=["GET"]
)  # Get recent schedules
schedule_routes.add_url_rule(
    "/<id>", view_func=get_schedule, methods=["GET"]
)  # Get one schedule
schedule_routes.add_url_rule(
    "/", view_func=add_schedule, methods=["POST"]
)  # Add a new schedule
schedule_routes.add_url_rule(
    "/<id>", view_func=update_schedule, methods=["PUT"]
)  # Update a schedule
schedule_routes.add_url_rule(
    "/<id>", view_func=delete_schedule, methods=["DELETE"]
)  # Delete a schedule
schedule_routes.add_url_rule("/", view_func=delete_all_schedules, methods=["DELETE"])
schedule_routes.add_url_rule(
    "/sync/google/classroom",
    view_func=sync_google_coursework_to_schedules,
    methods=["POST"],
)  # Sync Google Classroom schedules
schedule_routes.add_url_rule(
    "/sync/google/calendar",
    view_func=sync_google_calendar_to_schedules,
    methods=["POST"],
)  # Sync Google Calendar schedules
schedule_routes.add_url_rule(
    "/range", view_func=get_schedules_in_date_range_view, methods=["GET"]
)  # Get schedules within a specific time range

schedule_routes.add_url_rule(
    "/date/<date_str>", view_func=get_schedules_on_date_view, methods=["GET"]
)  # Get schedules on a specific date
