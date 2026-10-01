import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client["fake_job_detector"]

jobs_collection = db["jobs"]


def test_connection():
    try:
        client.admin.command("ping")
        print("MongoDB connected successfully")
    except Exception as e:
        print("MongoDB connection failed", e)