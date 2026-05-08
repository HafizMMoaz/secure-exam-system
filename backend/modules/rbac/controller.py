from flask import request

from responses import success_response, health_response
from modules.rbac.service import (
    get_permissions,
    check_access,
    list_users,
    toggle_user_status,
    get_health,
)


def permissions():
    user_context = getattr(request, "user", {})
    data = get_permissions(user_context)
    return success_response(data=data)


def check():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = check_access(user_context, payload)
    return success_response(data=data)


def users():
    role = request.args.get("role")
    data = list_users(role)
    return success_response(data=data)


def toggle(user_id):
    user_context = getattr(request, "user", {})
    data = toggle_user_status(user_id, actor_user_id=user_context.get("user_id"))
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
