from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["kanban_app"]

users_collection = db["users"]
projects_collection = db["projects"]

column_collection = db["columns"]
column_collection.create_index([("project", 1), ("order", 1)])

tasks_collection = db["tasks"]