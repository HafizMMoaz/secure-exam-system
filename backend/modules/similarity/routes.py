from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.similarity.controller import analyze, results, risk_data, health

similarity_bp = Blueprint("similarity_bp", __name__)


@similarity_bp.route("/analyze/<exam_id>", methods=["POST"])
@jwt_required
@role_required("teacher")
def analyze_route(exam_id):
    """
    Analyze answer similarity across all students for an exam.
    ---
    tags:
      - Similarity
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Similarity analysis completed
      403:
        description: Forbidden
    """
    return analyze(exam_id)


@similarity_bp.route("/results/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def results_route(exam_id):
    """
    Return the latest similarity analysis results for an exam.
    ---
    tags:
      - Similarity
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Similarity results returned
    """
    return results(exam_id)


@similarity_bp.route("/risk-data", methods=["GET"])
@jwt_required
def risk_data_route():
    """
    Return similarity risk data for aggregation.
    ---
    tags:
      - Similarity
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
        required: true
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Risk data returned
    """
    return risk_data()


@similarity_bp.route("/health", methods=["GET"])
def health_route():
    """
    Similarity module health check.
    ---
    tags:
      - Similarity
    security: []
    responses:
      200:
        description: Module health
    """
    return health()
