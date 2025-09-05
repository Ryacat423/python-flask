from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["kanban_app"]
users_collection = db["users"]


db_test = client["im2project"]
collection = db_test["products"]
