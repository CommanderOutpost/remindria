from pymongo import MongoClient
from config import config  # Import the Config class from config.py

# Initialize MongoDB connection
mongo_uri = f"mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/"
client = MongoClient(mongo_uri)
db = client[config.MONGO_DB]  # Use the database specified in config
