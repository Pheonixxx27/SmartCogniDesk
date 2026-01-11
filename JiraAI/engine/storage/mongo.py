from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = MongoClient(MONGO_URI)
db = client["jira_ai"]

logs_col = db["logs"]
events_col = db["events"]

def save_logs(logs):
    if logs:
        logs_col.insert_many(logs)

def save_events(events):
    if events:
        events_col.insert_many(events)
