from flask import Flask
from flask_cors import CORS

from exceptions import register_error_handlers
from responses import success_response
from config.swagger import init_swagger
from routes import register_routes

app = Flask(__name__)
CORS(app)

# ── Swagger docs at http://localhost:5000/api/docs ────────────────────────────
init_swagger(app)

# ── Register global error handlers ────────────────────────────────────────────
register_error_handlers(app)

register_routes(app)


# ── Global health check ───────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def global_health():
    """
    Global system health check.
    ---
    tags:
      - Health
    security: []
    responses:
      200:
        description: System is healthy
        schema:
          $ref: '#/definitions/SuccessResponse'
    """
    return success_response(
        data={"system": "secure-exam-system"},
        message="System is healthy"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)