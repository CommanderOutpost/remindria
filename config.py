# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI") or None
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
    MONGO_DB = os.getenv("MONGO_DB")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 1))
    )
    FLASK_ENV = os.getenv("FLASK_ENV") or "production"
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_ATLAS = os.getenv("MONGO_ATLAS", "False") == "True"
    SENTRY_DSN = os.getenv("SENTRY_DSN")

    @staticmethod
    def init_app(app):
        pass

    @staticmethod
    def validate():
        required_vars = [
            "MONGO_DB",
            "JWT_SECRET_KEY",
            "JWT_ACCESS_TOKEN_EXPIRES",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "OPENAI_MODEL",
        ]
        missing = [var for var in required_vars if not getattr(Config, var)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.DEBUG

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = logging.INFO

    @staticmethod
    def init_app(app):
        # Setup logging to file
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')

config = (
    DevelopmentConfig()
    if os.getenv("FLASK_ENV") == "development"
    else ProductionConfig()
)

print(config.FLASK_ENV)
