import math


def is_fast_answer(answer_time_seconds: float, threshold: float = 8.0) -> bool:
    return answer_time_seconds < threshold


def is_bulk_submission(submission_times: list[float], threshold_minutes: float = 2.0) -> bool:
    """submission_times: list of seconds-since-exam-start for each submission"""
    if len(submission_times) < 3:
        return False
    time_span = max(submission_times) - min(submission_times)
    return time_span < (threshold_minutes * 60)


def is_high_edit_frequency(edit_count: int, threshold: int = 3) -> bool:
    return edit_count > threshold


def is_late_submission_spike(submission_times: list[float], exam_duration_seconds: float) -> bool:
    """Check if > 50% of answers submitted in last 10% of exam time"""
    if not submission_times or exam_duration_seconds <= 0:
        return False
    cutoff = exam_duration_seconds * 0.9
    late_submissions = [t for t in submission_times if t >= cutoff]
    return len(late_submissions) > len(submission_times) * 0.5


def is_uniform_timing(answer_times: list[float], threshold_std: float = 3.0) -> bool:
    """Check if std deviation of answer times is suspiciously low"""
    if len(answer_times) < 3:
        return False
    mean = sum(answer_times) / len(answer_times)
    variance = sum((t - mean) ** 2 for t in answer_times) / len(answer_times)
    std_dev = math.sqrt(variance)
    return std_dev < threshold_std


def compute_suspicious_rule_count(flags: dict) -> int:
    """Count how many rules were triggered"""
    return sum(1 for v in flags.values() if v)


def analyze_behavior(events: list[dict], exam_duration_seconds: float) -> dict:
    """
    Main analysis function. Takes list of behavioral events and returns analysis.

    Each event dict has:
      { question_id, answer_time_seconds, submission_time_seconds,
        edit_count, submitted_at }

    Returns:
      {
        "fast_answer_count": int,
        "bulk_submit_flag": int (0 or 1),
        "answer_edit_count": int,
        "late_spike_flag": bool,
        "uniform_timing_flag": bool,
        "suspicious_rule_count": int,
        "flags": {
          "fast_answer": bool,
          "bulk_submission": bool,
          "high_edit_frequency": bool,
          "late_submission_spike": bool,
          "uniform_timing": bool
        }
      }
    """
    if not events:
        return {
            "fast_answer_count": 0,
            "bulk_submit_flag": 0,
            "answer_edit_count": 0,
            "late_spike_flag": False,
            "uniform_timing_flag": False,
            "suspicious_rule_count": 0,
            "flags": {
                "fast_answer": False,
                "bulk_submission": False,
                "high_edit_frequency": False,
                "late_submission_spike": False,
                "uniform_timing": False,
            },
        }

    answer_times = [e["answer_time_seconds"] for e in events]
    submission_times = [e["submission_time_seconds"] for e in events]
    total_edit_count = sum(e.get("edit_count", 0) for e in events)

    fast_answers = [t for t in answer_times if is_fast_answer(t)]
    bulk = is_bulk_submission(submission_times)
    high_edits = is_high_edit_frequency(total_edit_count)
    late_spike = is_late_submission_spike(submission_times, exam_duration_seconds)
    uniform = is_uniform_timing(answer_times)

    flags = {
        "fast_answer": len(fast_answers) > 0,
        "bulk_submission": bulk,
        "high_edit_frequency": high_edits,
        "late_submission_spike": late_spike,
        "uniform_timing": uniform,
    }

    return {
        "fast_answer_count": len(fast_answers),
        "bulk_submit_flag": 1 if bulk else 0,
        "answer_edit_count": total_edit_count,
        "late_spike_flag": late_spike,
        "uniform_timing_flag": uniform,
        "suspicious_rule_count": compute_suspicious_rule_count(flags),
        "flags": flags,
    }
