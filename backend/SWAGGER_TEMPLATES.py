"""
SWAGGER DOCSTRING REFERENCE
===========================
Copy-paste these templates into your route functions.
Flasgger reads the YAML inside the docstring automatically.

Docs live at: http://localhost:5500/api/docs
"""


# ── 1. Public endpoint (no JWT) ───────────────────────────────────────────────
def public_route_template():
    """
    Short one-line summary.
    ---
    tags:
      - Auth
    security: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: hafiz123
            password:
              type: string
              example: secret123
    responses:
      200:
        description: Success
        schema:
          $ref: '#/definitions/SuccessResponse'
      400:
        description: Missing or invalid parameters
        schema:
          $ref: '#/definitions/Error400'
      500:
        description: Internal server error
        schema:
          $ref: '#/definitions/Error500'
    """
    pass


# ── 2. Protected endpoint (JWT required) ──────────────────────────────────────
def protected_route_template():
    """
    Short one-line summary.
    ---
    tags:
      - Behavioral
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
              example: 64abc123
            answer_time_seconds:
              type: integer
              example: 5
    responses:
      200:
        description: Success
        schema:
          $ref: '#/definitions/SuccessResponse'
      400:
        description: Missing or invalid parameters
        schema:
          $ref: '#/definitions/Error400'
      401:
        description: Invalid or missing JWT
        schema:
          $ref: '#/definitions/Error401'
      403:
        description: Insufficient permissions
        schema:
          $ref: '#/definitions/Error403'
      409:
        description: Exam state violation
        schema:
          $ref: '#/definitions/Error409'
      500:
        description: Internal server error
        schema:
          $ref: '#/definitions/Error500'
    """
    pass


# ── 3. GET with query params ───────────────────────────────────────────────────
def get_with_query_params_template():
    """
    Short one-line summary.
    ---
    tags:
      - Behavioral
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: user_id
        type: string
        required: true
        description: The student's user ID
      - in: query
        name: exam_id
        type: string
        required: true
        description: The exam ID
    responses:
      200:
        description: Risk data returned
        schema:
          $ref: '#/definitions/RiskDataResponse'
      400:
        description: Missing parameters
        schema:
          $ref: '#/definitions/Error400'
      401:
        description: Invalid or missing JWT
        schema:
          $ref: '#/definitions/Error401'
    """
    pass


# ── 4. GET with URL path param ────────────────────────────────────────────────
def get_with_path_param_template():
    """
    Short one-line summary.
    ---
    tags:
      - Auth
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: exam_id
        type: string
        required: true
        description: The exam ID
    responses:
      200:
        description: Exam state returned
        schema:
          $ref: '#/definitions/SuccessResponse'
      404:
        description: Exam not found
        schema:
          $ref: '#/definitions/Error404'
    """
    pass


# ── 5. Health check (every module) ───────────────────────────────────────────
def health_check_template():
    """
    Module health check.
    ---
    tags:
      - Behavioral
    security: []
    responses:
      200:
        description: Module is healthy
        schema:
          $ref: '#/definitions/HealthResponse'
      503:
        description: Module or dependency is unhealthy
        schema:
          $ref: '#/definitions/Error503'
    """
    pass