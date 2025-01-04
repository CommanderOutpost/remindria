from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from config import config

# Load MongoDB URI from the config or environment variable
mongo_uri = os.getenv("MONGO_URI") or getattr(config, "MONGO_URI", None)

if not mongo_uri:
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

# MongoDB connection options for production-grade performance
client_options = {
    "maxPoolSize": 50,  # Maximum number of connections in the pool
    "minPoolSize": 5,   # Minimum number of connections in the pool
    "serverSelectionTimeoutMS": 5000,  # Timeout for server selection in ms
    "socketTimeoutMS": 10000,  # Timeout for socket operations in ms
    "connectTimeoutMS": 10000,  # Timeout for initial connection in ms
}

try:
    # Initialize MongoDB connection with options
    client = MongoClient(mongo_uri, **client_options)
    # Attempt to connect to verify the connection
    client.admin.command("ping")
    print("Connected to MongoDB successfully.")
except ConnectionFailure as e:
    raise Exception(f"Failed to connect to MongoDB: {e}")

# Select the database
db = client[getattr(config, "MONGO_DB", "default_db")]

# Define a helper function to get collections with indexes
def get_collection(name, indexes=None):
    """
    Get a MongoDB collection with optional index setup.

    Args:
        name (str): The name of the collection.
        indexes (list, optional): A list of index specifications. Each index is a tuple
                                   with the field name and direction (e.g., [("field", 1)]).

    Returns:
        pymongo.collection.Collection: The MongoDB collection.
    """
    collection = db[name]
    if indexes:
        for index in indexes:
            collection.create_index(index, background=True)
    return collection
