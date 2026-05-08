from flask import request

from responses import success_response, health_response

from modules.session.service import (
    create_session,
    invalidate_session,
    validate_session,
    list_sessions,
    get_health,
)


def create():
    user_context = getattr(request, "user", {})
    data = create_session(user_context)
    return success_response(data=data)


def invalidate():
    user_context = getattr(request, "user", {})
    session_id = user_context.get("session_id")
    invalidate_session(session_id)
    return success_response(message="Session invalidated")


def validate():
    user_context = getattr(request, "user", {})
    session_id = user_context.get("session_id")
    data = validate_session(session_id)
    return success_response(data=data)


def list_all():
    user_id = request.args.get("user_id")
    data = list_sessions(user_id)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
