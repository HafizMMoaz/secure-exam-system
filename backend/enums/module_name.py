from enum import Enum


class ModuleName(str, Enum):
    """
    Official module names - used in log entries and health check responses
    to ensure consistency across all modules.
    """
    AUTH           = "Module_1_Auth"
    SESSION        = "Module_2_Session"
    DEVICE         = "Module_3_Device"
    ACTIVATION     = "Module_4_Activation"
    RBAC           = "Module_5_RBAC"
    QUESTIONS      = "Module_6_Questions"
    RANDOMIZATION  = "Module_7_Randomization"
    TIMER          = "Module_8_Timer"
    VALIDATION     = "Module_9_Validation"
    TAB            = "Module_10_TabMonitor"
    CLIPBOARD      = "Module_11_Clipboard"
    ACTIVITY       = "Module_12_Activity"
    LOGGING        = "Module_13_Logging"
    MULTISESSION   = "Module_14_MultiSession"
    BEHAVIORAL     = "Module_15_Behavioral"
    SIMILARITY     = "Module_16_Similarity"
    RISK           = "Module_17_Risk"