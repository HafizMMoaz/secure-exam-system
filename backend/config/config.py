import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", 60))
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["exam_security"]

# Collections
users_col = db["users"]
devices_col = db["devices"]
exams_col = db["exams"]
questions_col = db["questions"]
responses_col = db["responses"]
logs_col = db["logs"]
risk_scores_col = db["risk_scores"]