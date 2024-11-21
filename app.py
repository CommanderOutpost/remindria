from flask import Flask
from flask_jwt_extended import JWTManager
from app.routes.schedule_routes import schedule_routes
from app.routes.auth_routes import auth_routes
from config import config

# Initialize the Flask app
app = Flask(__name__)

# Register the blueprints
app.register_blueprint(auth_routes, url_prefix="/auth")
app.register_blueprint(schedule_routes, url_prefix="/schedule")

app.config.from_object(config)

jwt = JWTManager(app)


if __name__ == "__main__":
    app.run(debug=True)
