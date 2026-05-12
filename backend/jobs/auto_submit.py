import threading
import time
import requests as http_requests
from bson import ObjectId

from config.config import exams_col, exam_sessions_col, responses_col, now, BASE_URL
from enums.exam_state import ExamState


def _auto_submit_expired_exams():
    """
    Runs every 60 seconds. Finds all exams past end_time that are still
    IN_PROGRESS or ACTIVATION_VALID and submits them automatically.
    """
    while True:
        try:
            current_time = now()

            expired_exams = exams_col.find(
                {
                    "state": {
                        "$in": [
                            ExamState.IN_PROGRESS.value,
                            ExamState.ACTIVATION_VALID.value,
                            ExamState.TEACHER_APPROVED.value,
                        ]
                    },
                    "end_time": {"$lt": current_time},
                }
            )

            for exam in expired_exams:
                exam_id = str(exam["_id"])
                try:
                    exam_sessions_col.update_many(
                        {"exam_id": exam_id, "is_active": True},
                        {
                            "$set": {
                                "is_active": False,
                                "submitted_at": current_time,
                                "auto_submitted": True,
                            }
                        },
                    )

                    exams_col.update_one(
                        {"_id": ObjectId(exam_id)},
                        {
                            "$set": {
                                "state": ExamState.SUBMITTED.value,
                                "auto_submitted_at": current_time,
                            }
                        },
                    )

                    http_requests.post(
                        f"{BASE_URL}/api/logs/write",
                        json={
                            "module": "Module_8_Timer",
                            "level": "WARNING",
                            "user_id": "system",
                            "exam_id": exam_id,
                            "action": "exam_auto_submitted",
                            "details": {"reason": "end_time_exceeded"},
                            "timestamp": current_time.isoformat(),
                        },
                        timeout=2,
                    )
                except Exception:
                    pass

        except Exception:
            pass

        time.sleep(60)


def start_auto_submit_job():
    """Start background thread for auto-submission. Call from app.py."""
    thread = threading.Thread(target=_auto_submit_expired_exams, daemon=True)
    thread.start()
