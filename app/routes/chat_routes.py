# app/routes/chat_routes.py

from flask import Blueprint
from app.views.chat_view import chat, get_chats, get_chat_by_id, delete_chat_by_id

chat_routes = Blueprint("chat", __name__)

chat_routes.add_url_rule("/", view_func=chat, methods=["POST"])
chat_routes.add_url_rule("/", view_func=get_chats, methods=["GET"])
chat_routes.add_url_rule("/<chat_id>", view_func=get_chat_by_id, methods=["GET"])
chat_routes.add_url_rule("/<chat_id>", view_func=delete_chat_by_id, methods=["DELETE"])
