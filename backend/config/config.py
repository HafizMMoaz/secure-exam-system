import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import pytz

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", 60))
MONGO_URI = os.getenv("MONGO_URI")

# Timezone configuration
TIMEZONE = os.getenv("TIMEZONE", "UTC")
APP_TZ = pytz.timezone(TIMEZONE)

# Base URL for internal service calls
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
# Port the Flask app should bind to when started via app.py
PORT = int(os.getenv("PORT", 5500))

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
sessions_col = db["sessions"]
activation_codes_col = db["activation_codes"]
randomized_orders_col = db["randomized_orders"]
exam_sessions_col = db["exam_sessions"]
tab_events_col = db["tab_events"]
clipboard_events_col = db["clipboard_events"]
activity_events_col = db["activity_events"]
multisession_attempts_col = db["multisession_attempts"]


def now():
	"""Return current datetime in the configured app timezone."""
	return datetime.now(APP_TZ)