from responses import success_response
from modules.auth.service import get_health as get_auth_health
from modules.activation.service import get_health as get_activation_health
from modules.session.service import get_health as get_session_health
from modules.device.service import get_health as get_device_health
from modules.logging.service import get_health as get_logging_health


def _module_health(module_name, health_data=None, healthy=False):
    data = health_data or {
        "module_name": module_name,
        "dependencies": ["mongodb"],
        "version": "1.0.0",
        "healthy": healthy,
    }
    return {
        "module_name": data.get("module_name", module_name),
        "status": "healthy" if data.get("healthy") else "unhealthy",
        "dependencies": data.get("dependencies", ["mongodb"]),
        "version": data.get("version", "1.0.0"),
        "healthy": data.get("healthy", False),
    }


def global_health():
    modules = [
        _module_health("Module_1_Auth", get_auth_health()),
        _module_health("Module_2_Session", get_session_health()),
        _module_health("Module_3_Device", get_device_health()),
        _module_health("Module_4_Activation", get_activation_health()),
        _module_health("Module_5_RBAC"),
        _module_health("Module_6_Questions"),
        _module_health("Module_7_Randomization"),
        _module_health("Module_8_Timer"),
        _module_health("Module_9_Validation"),
        _module_health("Module_10_TabMonitor"),
        _module_health("Module_11_Clipboard"),
        _module_health("Module_12_Activity"),
        _module_health("Module_13_Logging", get_logging_health()),
        _module_health("Module_14_MultiSession"),
        _module_health("Module_15_Behavioral"),
        _module_health("Module_16_Similarity"),
        _module_health("Module_17_Risk"),
    ]

    healthy_modules = sum(1 for module in modules if module["healthy"])

    return success_response(
        data={
            "system": "secure-exam-system",
            "modules": modules,
            "healthy_modules": healthy_modules,
            "total_modules": len(modules),
        },
        message="System health snapshot generated",
    )
