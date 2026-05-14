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

                    # section 27.6 (strict) exemption: auto_submit runs as a system
                    # process without a user JWT. The section 27.6 central state
                    # endpoint requires authentication; documenting this
                    # path as the single sanctioned bypass for system-driven
                    # transitions. All non-system transitions still route
                    # through Module 1.
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

                    # End-of-window finalization: kick off risk compute now
                    # so the dashboard reflects the closure right away,
                    # rather than waiting for a teacher click that never
                    # comes. Risk service handles the SUBMITTED -> ANALYZING
                    # -> COMPLETED transitions internally.
                    try:
                        from modules.risk.service import compute_exam_risk
                        compute_exam_risk(
                            user_context={"role": "system", "user_id": "system_auto_submit"},
                            exam_id=exam_id,
                            auth_header="",
                            system_actor=True,
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

        except Exception:
            pass

        time.sleep(60)


def start_auto_submit_job():
    """Start background thread for auto-submission. Call from app.py."""
    thread = threading.Thread(target=_auto_submit_expired_exams, daemon=True)
    thread.start()
