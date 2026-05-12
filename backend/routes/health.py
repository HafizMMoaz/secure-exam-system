from responses import success_response
from modules.auth.service import get_health as get_auth_health
from modules.session.service import get_health as get_session_health
from modules.device.service import get_health as get_device_health
from modules.activation.service import get_health as get_activation_health
from modules.rbac.service import get_health as get_rbac_health
from modules.questions.service import get_health as get_questions_health
from modules.randomization.service import get_health as get_randomization_health
from modules.timer.service import get_health as get_timer_health
from modules.validation.service import get_health as get_validation_health
from modules.tab.service import get_health as get_tab_health
from modules.clipboard.service import get_health as get_clipboard_health
from modules.activity.service import get_health as get_activity_health
from modules.logging.service import get_health as get_logging_health
from modules.multisession.service import get_health as get_multisession_health
from modules.behavioral.service import get_health as get_behavioral_health
from modules.similarity.service import get_health as get_similarity_health
from modules.risk.service import get_health as get_risk_health


def _module_health(module_name, health_data):
    return {
        "module_name": health_data.get("module_name", module_name),
        "status": "healthy" if health_data.get("healthy") else "unhealthy",
        "dependencies": health_data.get("dependencies", ["mongodb"]),
        "version": health_data.get("version", "1.0.0"),
        "healthy": health_data.get("healthy", False),
    }


def _safe_health(label, fetcher):
    try:
        return _module_health(label, fetcher())
    except Exception:
        return _module_health(label, {"healthy": False})


def global_health():
    modules = [
        _safe_health("Module_1_Auth", get_auth_health),
        _safe_health("Module_2_Session", get_session_health),
        _safe_health("Module_3_Device", get_device_health),
        _safe_health("Module_4_Activation", get_activation_health),
        _safe_health("Module_5_RBAC", get_rbac_health),
        _safe_health("Module_6_Questions", get_questions_health),
        _safe_health("Module_7_Randomization", get_randomization_health),
        _safe_health("Module_8_Timer", get_timer_health),
        _safe_health("Module_9_Validation", get_validation_health),
        _safe_health("Module_10_TabMonitor", get_tab_health),
        _safe_health("Module_11_Clipboard", get_clipboard_health),
        _safe_health("Module_12_Activity", get_activity_health),
        _safe_health("Module_13_Logging", get_logging_health),
        _safe_health("Module_14_MultiSession", get_multisession_health),
        _safe_health("Module_15_Behavioral", get_behavioral_health),
        _safe_health("Module_16_Similarity", get_similarity_health),
        _safe_health("Module_17_Risk", get_risk_health),
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
