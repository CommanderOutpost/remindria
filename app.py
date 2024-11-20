from flask import Flask
from flask_jwt_extended import JWTManager
from app.routes.auth_routes import auth_routes  # Import your auth blueprint
from config import config

# Initialize the Flask app
app = Flask(__name__)

# Register the blueprints
app.register_blueprint(auth_routes, url_prefix="/auth")
app.config.from_object(config)

jwt = JWTManager(app)


if __name__ == "__main__":
    app.run(debug=True)
