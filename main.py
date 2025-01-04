from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import time  # Import for tracking request time
from app.routes.chat_routes import chat_routes
from app.routes.schedule_routes import schedule_routes
from app.routes.auth_routes import auth_routes
from app.routes.token_routes import token_routes
from app.routes.other_routes import other_routes
from config import Config, config

# Initialize the Flask app
app = Flask(__name__)

# Enable CORS
if config.FLASK_ENV == "production":
    CORS(app, origins=["https://yourdomain.com"])
else:
    CORS(app)
    
# Register the blueprints
app.register_blueprint(auth_routes, url_prefix="/auth")
app.register_blueprint(schedule_routes, url_prefix="/schedule")
app.register_blueprint(other_routes, url_prefix="/other")
app.register_blueprint(chat_routes, url_prefix="/chat")
app.register_blueprint(token_routes, url_prefix="/token")

app.config.from_object(config)

config.validate()

config.init_app(app)

if not app.debug and not app.testing:
    Config.init_app(app)

jwt = JWTManager(app)


@app.before_request
def start_timer():
    """
    Start a timer before handling a request.
    """
    g.start_time = time.time()


@app.after_request
def log_request(response):
    if hasattr(g, "start_time"):
        elapsed_time = (time.time() - g.start_time) * 1000  # ms
        app.logger.info(
            f"{request.method} {request.path} {response.status_code} {elapsed_time:.2f}ms"
        )
    return response



if __name__ == "__main__":
    if app.config["FLASK_ENV"] == "production":
        app.run()
    else:
        app.run(debug=True)
