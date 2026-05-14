from enum import Enum


class RiskMetric(str, Enum):
    """
    Risk metric keys - used in GET /api/module/risk-data responses (section 27.7).
    Module 17 reads these to compute the final risk score.

    Risk Score formula (section 17):
        (0.3 * tab_switch_count)
      + (0.2 * idle_time_seconds)
      + (0.3 * similarity_score)
      + (0.2 * fast_answer_count)
    """
    # Module 10 - Tab Monitor
    TAB_SWITCH_COUNT       = "tab_switch_count"

    # Module 11 - Clipboard
    CLIPBOARD_PASTE_COUNT  = "clipboard_paste_count"
    CLIPBOARD_COPY_COUNT   = "clipboard_copy_count"

    # Module 12 - Activity
    IDLE_TIME_SECONDS      = "idle_time_seconds"

    # Module 14 - Multi Session
    MULTI_SESSION_ATTEMPTS = "multi_session_attempts"

    # Module 15 - Behavioral
    FAST_ANSWER_COUNT      = "fast_answer_count"
    BULK_SUBMIT_FLAG       = "bulk_submit_flag"
    ANSWER_EDIT_COUNT      = "answer_edit_count"
    SUSPICIOUS_RULE_COUNT  = "suspicious_rule_count"

    # Module 16 - Similarity
    SIMILARITY_SCORE       = "similarity_score"