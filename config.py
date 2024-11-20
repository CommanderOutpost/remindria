import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_PORT = os.getenv("MONGO_PORT")
    MONGO_DB = os.getenv("MONGO_DB")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")


config = Config()
