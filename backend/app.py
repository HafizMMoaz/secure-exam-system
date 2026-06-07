from flask import Flask, redirect, request
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
allowed_origins = [origin.strip().rstrip("/") for origin in FRONTEND_URL.split(",") if origin.strip()]
default_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
for origin in default_dev_origins:
  if origin not in allowed_origins:
    allowed_origins.append(origin)
frontend_redirect_url = allowed_origins[0] if allowed_origins else FRONTEND_URL

CORS(
  app,
  resources={r"/api/*": {"origins": allowed_origins}},
  supports_credentials=True,
  allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
  methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


@app.after_request
def add_cors_headers(response):
  origin = request.headers.get("Origin", "").rstrip("/")
  if origin and origin in allowed_origins:
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
  return response

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