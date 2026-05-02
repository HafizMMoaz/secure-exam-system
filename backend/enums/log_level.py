from enum import Enum


class LogLevel(str, Enum):
    """
    Log levels — from logging gateway spec section 27.3.
    level: "INFO | WARNING | ERROR | SECURITY"
    """
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    SECURITY = "SECURITY"