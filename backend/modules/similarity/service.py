import requests
from collections import defaultdict

from bson import ObjectId
from pymongo.errors import PyMongoError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.config import responses_col, exams_col, similarity_results_col, BASE_URL, now
from enums.module_name import ModuleName
from enums.log_level import LogLevel
from enums.risk_metric import RiskMetric
from exceptions import BadRequestException, DatabaseException, ExamNotFoundException, ForbiddenException


def _iso(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _send_log(level, user_id, action, details):
    payload = {
        "module": ModuleName.SIMILARITY.value,
        "level": level,
        "user_id": user_id or "",
        "exam_id": details.get("exam_id") if details else "",
        "action": action,
        "details": details or {},
        "timestamp": now().isoformat(),
    }
    try:
        requests.post(f"{BASE_URL}/api/logs/write", json=payload, timeout=2)
    except Exception:
        pass


def compute_similarity_matrix(answers: list[dict]) -> list[dict]:
    """
    answers: list of { student_id, answer_text }
    Returns: list of { student_a, student_b, similarity_score, is_suspicious }
    Threshold: 0.85
    """
    if len(answers) < 2:
        return []

    texts = [a["answer_text"] for a in answers]
    student_ids = [a["student_id"] for a in answers]

    vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    similarity_matrix = cosine_similarity(tfidf_matrix)
    results = []

    for i in range(len(student_ids)):
        for j in range(i + 1, len(student_ids)):
            score = float(similarity_matrix[i][j])
            results.append(
                {
                    "student_a": student_ids[i],
                    "student_b": student_ids[j],
                    "similarity_score": round(score, 4),
                    "is_suspicious": score >= 0.85,
                }
            )

    return results


def _normalize_pair(student_a, student_b):
    return tuple(sorted((str(student_a), str(student_b))))


def analyze_exam_similarity(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    user_role = (user_context or {}).get("role")
    if user_role != "teacher":
        raise ForbiddenException("Only teachers can analyze similarity")

    try:
        exam = exams_col.find_one({"_id": ObjectId(exam_id)})
    except Exception:
        try:
            exam = exams_col.find_one({"_id": exam_id})
        except Exception:
            exam = None

    if not exam:
        raise ExamNotFoundException()

    try:
        exam_responses = list(responses_col.find({"exam_id": exam_id}))
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    grouped = defaultdict(list)
    for response in exam_responses:
        grouped[str(response.get("question_id"))].append(
            {
                "student_id": str(response.get("student_id")),
                "answer_text": response.get("answer_text", "") or "",
            }
        )

    question_results = []
    pair_counts = defaultdict(int)
    all_students = set()

    for question_id, answers in grouped.items():
        all_students.update(answer["student_id"] for answer in answers)
        pairs = compute_similarity_matrix(answers)
        question_results.append({"question_id": question_id, "pairs": pairs})
        for pair in pairs:
            if pair.get("is_suspicious"):
                pair_key = _normalize_pair(pair["student_a"], pair["student_b"])
                pair_counts[pair_key] += 1

    suspicious_pairs = [
        {
            "student_a": pair_key[0],
            "student_b": pair_key[1],
            "suspicious_question_count": count,
        }
        for pair_key, count in pair_counts.items()
        if count >= 1
    ]

    result_doc = {
        "exam_id": exam_id,
        "analyzed_by": (user_context or {}).get("user_id"),
        "analyzed_at": now(),
        "question_results": question_results,
        "suspicious_pairs": suspicious_pairs,
        "total_students": len(all_students),
        "total_questions_analyzed": len(question_results),
    }

    try:
        similarity_results_col.insert_one(result_doc)
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if suspicious_pairs:
        _send_log(
            LogLevel.SECURITY.value,
            (user_context or {}).get("user_id"),
            "similarity_suspicious_pairs_found",
            {"exam_id": exam_id, "suspicious_pair_count": len(suspicious_pairs)},
        )

    return {
        "exam_id": exam_id,
        "total_students": len(all_students),
        "total_questions_analyzed": len(question_results),
        "suspicious_pairs": suspicious_pairs,
        "suspicious_pair_count": len(suspicious_pairs),
    }


def get_latest_results(user_context, exam_id):
    if not exam_id:
        raise BadRequestException("exam_id is required")

    if (user_context or {}).get("role") != "teacher":
        raise ForbiddenException("Only teachers can view similarity results")

    try:
        result = similarity_results_col.find_one({"exam_id": exam_id}, sort=[("analyzed_at", -1)])
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    if not result:
        return {"message": "No similarity analysis run yet for this exam"}

    return {
        "exam_id": result.get("exam_id"),
        "analyzed_at": _iso(result.get("analyzed_at")),
        "question_results": result.get("question_results", []),
        "suspicious_pairs": result.get("suspicious_pairs", []),
        "total_students": result.get("total_students", 0),
        "total_questions_analyzed": result.get("total_questions_analyzed", 0),
    }


def get_risk_data(user_id, exam_id):
    if not user_id:
        raise BadRequestException("user_id is required")
    if not exam_id:
        raise BadRequestException("exam_id is required")

    try:
        result = similarity_results_col.find_one({"exam_id": exam_id}, sort=[("analyzed_at", -1)])
    except PyMongoError as exc:
        raise DatabaseException(str(exc))

    highest_score = 0.0
    if result:
        for question_result in result.get("question_results", []):
            for pair in question_result.get("pairs", []):
                if user_id in {str(pair.get("student_a")), str(pair.get("student_b"))}:
                    highest_score = max(highest_score, float(pair.get("similarity_score", 0.0)))

    return [
        {
            "user_id": user_id,
            "exam_id": exam_id,
            "timestamp": now().isoformat(),
            "metric": RiskMetric.SIMILARITY_SCORE.value,
            "value": highest_score,
        }
    ]


def get_health():
    return {"module_name": ModuleName.SIMILARITY.value, "dependencies": ["mongodb"], "version": "1.0.0", "healthy": True}
