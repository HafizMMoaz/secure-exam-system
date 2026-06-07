from flask import Blueprint

from middleware.jwt_auth import jwt_required, role_required
from modules.questions.controller import (
  approve_exam_route,
  approve_student_route,
  create,
  create_exam_route,
  delete_exam_route,
  delete_question_route,
  enroll_student_route,
  get_exam_route,
  get_exam_public_route,
  get_exam_students_route,
  get_exam_results_route,
  list_student_results_route,
  list_all_for_student_route,
  list_answers_route,
  list_all,
  list_exams_route,
  save_answer_route,
  update_exam_route,
  update_question_route,
  health,
)

questions_bp = Blueprint("questions_bp", __name__)


@questions_bp.route("/create", methods=["POST"])
@jwt_required
@role_required("teacher")
def create_route():
    """
    Create a question for an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
            - text
            - options
            - correct_answer
          properties:
            exam_id:
              type: string
            text:
              type: string
            options:
              type: array
              items:
                type: string
            correct_answer:
              type: string
            marks:
              type: integer
    responses:
      200:
        description: Question created
      400:
        description: Bad request
    """
    return create()


@questions_bp.route("/exam/<exam_id>/all", methods=["GET"])
@jwt_required
@role_required("student")
def all_questions_for_student_route(exam_id):
    """
    Get all exam questions for the authenticated student.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Questions returned
      401:
        description: Invalid or missing JWT
      403:
        description: Exam not in progress
    """
    return list_all_for_student_route(exam_id)


@questions_bp.route("/answer/save", methods=["POST"])
@jwt_required
@role_required("student")
def save_answer_bp_route():
    """
    Save one student answer.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
            - question_id
            - answer
            - time_taken_seconds
          properties:
            exam_id:
              type: string
            question_id:
              type: string
            answer:
              type: string
            time_taken_seconds:
              type: number
    responses:
      200:
        description: Answer saved
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
    """
    return save_answer_route()


@questions_bp.route("/answer/list", methods=["GET"])
@jwt_required
@role_required("student")
def list_answers_bp_route():
    """
    List saved answers for the authenticated student in an exam.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Answers returned
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
    """
    return list_answers_route()


@questions_bp.route("/list/<exam_id>", methods=["GET"])
@jwt_required
@role_required("teacher")
def list_route(exam_id):
    """
    List all questions for an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Questions listed
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_all(exam_id)


@questions_bp.route("/health", methods=["GET"])
def health_route():
    """
    Questions module health check.
    ---
    tags:
      - Questions
    security: []
    responses:
      200:
        description: Module health
    """
    return health()


@questions_bp.route("/exams/create", methods=["POST"])
@jwt_required
@role_required("teacher")
def create_exam_bp_route():
    """
    Create a new exam.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - duration_minutes
          properties:
            title:
              type: string
            description:
              type: string
            duration_minutes:
              type: integer
              minimum: 10
              maximum: 180
            approval_mode:
              type: string
              enum: [manual, code, both]
              default: both
    responses:
      200:
        description: Exam created
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return create_exam_route()


@questions_bp.route("/exams/list", methods=["GET"])
@jwt_required
@role_required("teacher")
def exams_list_bp_route():
    """
    List exams created by the authenticated teacher.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    responses:
      200:
        description: Exams listed
      401:
        description: Invalid or missing JWT
      403:
        description: Insufficient permissions
    """
    return list_exams_route()


@questions_bp.route("/exams/<exam_id>", methods=["GET"])
@jwt_required
def exam_detail_bp_route(exam_id):
    """
    Get full exam details.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Exam returned
      401:
        description: Invalid or missing JWT
      404:
        description: Exam not found
    """
    return get_exam_route(exam_id)


@questions_bp.route("/exams/public/<exam_id>", methods=["GET"])
@jwt_required
def exam_public_bp_route(exam_id):
    """
    Get safe public exam details.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Public exam returned
      401:
        description: Invalid or missing JWT
      404:
        description: Exam not found
    """
    return get_exam_public_route(exam_id)


@questions_bp.route("/exams/approve", methods=["POST"])
@jwt_required
@role_required("teacher")
def approve_exam_bp_route():
    """
    Approve an exam for activation.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
          properties:
            exam_id:
              type: string
    responses:
      200:
        description: Exam approved
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
      409:
        description: Invalid exam state
    """
    return approve_exam_route()


@questions_bp.route("/exams/enroll", methods=["POST"])
@jwt_required
@role_required("student")
def enroll_student_bp_route():
    """
    Enroll the authenticated student into an exam.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
          properties:
            exam_id:
              type: string
    responses:
      200:
        description: Student enrolled
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
      409:
        description: Exam full or invalid state
    """
    return enroll_student_route()


@questions_bp.route("/exams/<exam_id>", methods=["PUT"])
@jwt_required
@role_required("teacher")
def update_exam_bp_route(exam_id):
    """
    Update an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            title:
              type: string
            description:
              type: string
            duration_minutes:
              type: integer
            max_students:
              type: integer
            start_time:
              type: string
            end_time:
              type: string
    responses:
      200:
        description: Exam updated
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
    """
    return update_exam_route(exam_id)


@questions_bp.route("/exams/<exam_id>", methods=["DELETE"])
@jwt_required
@role_required("teacher")
def delete_exam_bp_route(exam_id):
    """
    Delete an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Exam deleted
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
      409:
        description: Cannot delete - exam in progress or has students
    """
    return delete_exam_route(exam_id)


@questions_bp.route("/<question_id>", methods=["PUT"])
@jwt_required
@role_required("teacher")
def update_question_bp_route(question_id):
    """
    Update a question (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: question_id
        type: string
        required: true
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            text:
              type: string
            question_type:
              type: string
            options:
              type: array
            correct_answer:
              type: string
            marks:
              type: integer
            word_limit:
              type: integer
    responses:
      200:
        description: Question updated
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Question not found
    """
    return update_question_route(question_id)


@questions_bp.route("/<question_id>", methods=["DELETE"])
@jwt_required
@role_required("teacher")
def delete_question_bp_route(question_id):
    """
    Delete a question (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: question_id
        type: string
        required: true
    responses:
      200:
        description: Question deleted
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Question not found
    """
    return delete_question_route(question_id)


@questions_bp.route("/exams/<exam_id>/students", methods=["GET"])
@jwt_required
@role_required("teacher")
def get_exam_students_bp_route(exam_id):
    """
    Get list of students who joined an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Students returned
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
    """
    return get_exam_students_route(exam_id)


@questions_bp.route("/exams/<exam_id>/results", methods=["GET"])
@jwt_required
@role_required("teacher")
def get_exam_results_bp_route(exam_id):
    """
    Auto-marked per-student exam results (teacher only).
    Available once the exam has ended.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
    responses:
      200:
        description: Results returned
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam not found
    """
    return get_exam_results_route(exam_id)


@questions_bp.route("/exams/results/me", methods=["GET"])
@jwt_required
@role_required("student")
def list_student_results_bp_route():
    """
    List previous exam results for the authenticated student.
    Includes exams that are completed or past end_time.
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    responses:
      200:
        description: Student results returned
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
    """
    return list_student_results_route()


@questions_bp.route("/exams/students/approve", methods=["POST"])
@jwt_required
@role_required("teacher")
def approve_student_bp_route():
    """
    Approve a student to take an exam (teacher only).
    ---
    tags:
      - Questions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - exam_id
            - student_id
          properties:
            exam_id:
              type: string
            student_id:
              type: string
    responses:
      200:
        description: Student approved
      400:
        description: Bad request
      401:
        description: Invalid or missing JWT
      403:
        description: Forbidden
      404:
        description: Exam or student not found
    """
    return approve_student_route()
