from pymongo import MongoClient
from bson.objectid import ObjectId

class MongoService:
    def __init__(self, mongo_uri, db_name, collection_name):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_result(self, result_record):
        return self.collection.insert_one(result_record)

    def get_all_records(self):
        return self.collection.find({}, {'_id': 1, 'url': 1, 'domain': 1, 'date': 1})

    def get_record_by_id(self, record_id):
        return self.collection.find_one({"_id": ObjectId(record_id)})

    def get_records_by_domain(self, domain):
        return self.collection.find({"domain": domain}, {'_id': 1, 'url': 1, 'domain': 1, 'date': 1})
