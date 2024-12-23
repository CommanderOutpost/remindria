from pymongo import MongoClient
from config import config  # Import the Config class from config.py

# Check if Atlas format should be used
if hasattr(config, "MONGO_ATLAS") and config.MONGO_ATLAS:
    # MongoDB Atlas URI
    mongo_uri = f"mongodb+srv://{config.MONGO_USERNAME}:{config.MONGO_PASSWORD}@{config.MONGO_HOST}/"
else:
    # Local MongoDB URI
    if (
        hasattr(config, "MONGO_USERNAME")
        and hasattr(config, "MONGO_PASSWORD")
        and config.MONGO_USERNAME
        and config.MONGO_PASSWORD
    ):
        mongo_uri = f"mongodb://{config.MONGO_USERNAME}:{config.MONGO_PASSWORD}@{config.MONGO_HOST}:{config.MONGO_PORT}/"
    else:
        mongo_uri = f"mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/"

# Initialize MongoDB connection
client = MongoClient(mongo_uri)
db = client[config.MONGO_DB]  # Use the database specified in config
