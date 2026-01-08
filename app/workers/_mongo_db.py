from config.config import Config
import pymongo


try:
    client = pymongo.MongoClient(Config.MONGO_DB_URI)
  
# return a friendly error if a URI error is thrown 
except Exception as e:
    print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
    raise(e)

    
db = client[Config.MAPILLARY_DB_NAME]
collection = db[Config.MAPILLARY_IMAGE_COLLECTION]
