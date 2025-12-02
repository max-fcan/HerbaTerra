from config.config import Config
from pymongo import MongoClient

client = MongoClient(Config.MONGO_DB_URI)
db = client[Config.MAPILLARY_DB_NAME]
collection = db[Config.MAPILLARY_IMAGE_COLLECTION]
