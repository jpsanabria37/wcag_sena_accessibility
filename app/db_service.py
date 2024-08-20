from pymongo import MongoClient

class MongoService:
    def __init__(self, uri, db_name, collection_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_result(self, result):
        return self.collection.insert_one(result).inserted_id
