from flask import request

from middleware.jwt_auth import jwt_required, role_required
from responses import accepted_response, success_response, health_response

from modules.logging.service import write_log, verify_log, list_logs
from enums.module_name import ModuleName


def write():
    payload = request.get_json(silent=True) or {}
    write_log(payload)
    return accepted_response("Log entry recorded")


def verify(log_id):
    data = verify_log(log_id)
    return success_response(data=data)


def list_entries():
    filters = {
        "user_id": request.args.get("user_id"),
        "exam_id": request.args.get("exam_id"),
        "level": request.args.get("level"),
        "module": request.args.get("module"),
    }
    data = list_logs(filters)
    return success_response(data=data)


def health():
    return health_response(
        module_name=ModuleName.LOGGING.value,
        dependencies=["mongodb"],
        version="1.0.0",
        healthy=True,
    )
