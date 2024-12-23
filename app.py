from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import time  # Import for tracking request time
from app.routes.chat_routes import chat_routes
from app.routes.schedule_routes import schedule_routes
from app.routes.auth_routes import auth_routes
from app.routes.token_routes import token_routes
from app.routes.other_routes import other_routes
from config import config

# Initialize the Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Register the blueprints
app.register_blueprint(auth_routes, url_prefix="/auth")
app.register_blueprint(schedule_routes, url_prefix="/schedule")
app.register_blueprint(other_routes, url_prefix="/other")
app.register_blueprint(chat_routes, url_prefix="/chat")
app.register_blueprint(token_routes, url_prefix="/token")

app.config.from_object(config)

jwt = JWTManager(app)


@app.before_request
def start_timer():
    """
    Start a timer before handling a request.
    """
    g.start_time = time.time()


@app.after_request
def log_request(response):
    """
    Log the time taken to process a request and attach it to the response.
    """
    if hasattr(g, "start_time"):
        elapsed_time = (time.time() - g.start_time) * 1000  # Convert to ms
        # Log the method, path, status code, and time taken
        print(
            f" {elapsed_time:.2f}ms"
        )
    return response


if __name__ == "__main__":
    if config.FLASK_ENV == "production":
        app.run()
    app.run(debug=True)
