from flask import Response, request, stream_with_context

from responses import success_response, health_response
from modules.risk.service import compute_exam_risk, get_dashboard, get_student_score, get_health, stream_events


def stream(exam_id):
    return Response(
        stream_with_context(stream_events(exam_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def compute(exam_id):
    user_context = getattr(request, "user", {})
    auth_header = request.headers.get("Authorization", "")
    data = compute_exam_risk(user_context, exam_id, auth_header)
    return success_response(data=data)


def dashboard(exam_id):
    data = get_dashboard(exam_id)
    return success_response(data=data)


def student(student_id):
    user_context = getattr(request, "user", {})
    exam_id = request.args.get("exam_id")
    data = get_student_score(user_context, student_id, exam_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
