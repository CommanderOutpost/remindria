from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.routes.chat_routes import chat_routes
from app.routes.schedule_routes import schedule_routes
from app.routes.auth_routes import auth_routes
from app.routes.token_routes import token_routes
from config import config

# Initialize the Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Register the blueprints
app.register_blueprint(auth_routes, url_prefix="/auth")
app.register_blueprint(schedule_routes, url_prefix="/schedule")
app.register_blueprint(chat_routes, url_prefix="/chat")
app.register_blueprint(token_routes, url_prefix="/token")

app.config.from_object(config)

jwt = JWTManager(app)


if __name__ == "__main__":
    if config.FLASK_ENV == "production":
        app.run()
    app.run(debug=True)
