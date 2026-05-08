from flask import request

from responses import success_response, health_response
from modules.device.service import register_device, verify_device, list_devices, get_health


def register():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = register_device(user_context, payload)
    return success_response(data=data)


def verify():
    user_context = getattr(request, "user", {})
    payload = request.get_json(silent=True) or {}
    data = verify_device(user_context, payload)
    return success_response(data=data)


def list_all():
    user_context = getattr(request, "user", {})
    data = list_devices(user_context)
    return success_response(data=data)


def health():
    data = get_health()
    return health_response(**data)
