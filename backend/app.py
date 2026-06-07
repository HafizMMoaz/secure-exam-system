from flask import Flask, redirect
from flask_cors import CORS

from exceptions import register_error_handlers
from config.swagger import init_swagger
from routes import register_routes
from routes.health import global_health as get_global_health
from config.config import PORT, FRONTEND_URL
from jobs import start_auto_submit_job
from middleware.rate_limit import limiter
from middleware.socketio_app import socketio

app = Flask(__name__)
allowed_origins = [origin.strip() for origin in FRONTEND_URL.split(",") if origin.strip()]
frontend_redirect_url = allowed_origins[0] if allowed_origins else FRONTEND_URL

CORS(app, origins=allowed_origins, supports_credentials=True)

# Swagger docs at http://localhost:5500/api/docs 
init_swagger(app)

# Register global error handlers
register_error_handlers(app)

# Rate limiting (Phase 5.4)─
limiter.init_app(app)

# WebSocket monitoring channel (PRD section 24 bonus)
socketio.init_app(app, cors_allowed_origins=allowed_origins + ["*"])

register_routes(app)
start_auto_submit_job()


# Global health check
@app.route("/", methods=["GET"])
def root_redirect():
  return redirect(frontend_redirect_url, code=302)


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
    return get_global_health()


if __name__ == "__main__":
  socketio.run(app, host="0.0.0.0", port=PORT, debug=True, allow_unsafe_werkzeug=True)