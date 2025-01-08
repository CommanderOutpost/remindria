# app/__init__.py
from flask import Flask, g, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient, errors
import time

from config import config
from app.routes.chat_routes import chat_routes
from app.routes.schedule_routes import schedule_routes
from app.routes.auth_routes import auth_routes
from app.routes.token_routes import token_routes
from app.routes.other_routes import other_routes


def create_app():
    app = Flask(__name__)

    # Apply configuration
    app.config.from_object(config)
    config.init_app(app)
    config.validate()

    # Initialize logging
    if not app.debug:
        app.logger.info("Starting in production mode")

    # Setup CORS
    if app.config["FLASK_ENV"] == "production":
        CORS(app, origins=["https://yourdomain.com"])
    else:
        CORS(app)

    # Register blueprints
    app.register_blueprint(auth_routes, url_prefix="/auth")
    app.register_blueprint(schedule_routes, url_prefix="/schedule")
    app.register_blueprint(other_routes, url_prefix="/other")
    app.register_blueprint(chat_routes, url_prefix="/chat")
    app.register_blueprint(token_routes, url_prefix="/token")

    # Initialize JWT
    jwt = JWTManager(app)

    # Request timing
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        if hasattr(g, "start_time"):
            elapsed_time = (time.time() - g.start_time) * 1000  # ms
            app.logger.info(
                f"{request.method} {request.path} {response.status_code} {elapsed_time:.2f}ms"
            )
        return response

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Server Error: {error}, Path: {request.path}")
        return jsonify({"error": "Internal Server Error"}), 500
    
    # Command to list all routes
    @app.cli.command("list-routes")
    def list_routes():
        """List all routes in the application."""
        for rule in app.url_map.iter_rules():
            methods = ', '.join(rule.methods)
            print(f"{rule.endpoint:30s} {methods:20s} {rule.rule}")

    return app
