"""
Auth-endpoint rate limiting (Phase 5.4, Module 1).

Centralizes the Flask-Limiter instance so it can be initialized in app.py
and applied to specific endpoints via decorators. Defaults:

- 5 requests / minute / IP on /api/auth/login and /api/auth/otp/request
  (mitigates credential stuffing and OTP issuance abuse)
- 10 requests / minute / IP on /api/auth/otp/verify
  (mitigates code brute force; service-side OTP_MAX_ATTEMPTS still applies)

Storage is in-memory by default (per process). Real deployments should set
RATELIMIT_STORAGE_URI to a redis URL.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)


AUTH_LOGIN_LIMIT = "5 per minute"
AUTH_OTP_REQUEST_LIMIT = "5 per minute"
AUTH_OTP_VERIFY_LIMIT = "10 per minute"
