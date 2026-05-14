"""
Flask-SocketIO singleton + monitoring namespace (PRD section 24 bonus: WebSockets).

Sits alongside the SSE stream - same data, different transport. The SSE
endpoint stays in place for clients that block WebSocket upgrades (proxy
quirks); the SocketIO namespace gives a real bidirectional WS channel
for everyone else.

Clients subscribe to an exam room by emitting `subscribe { exam_id }`
on the `/monitoring` namespace. Monitoring modules push events here by
calling `emit_monitoring_event(exam_id, kind, payload)`.

async_mode is `threading` so we do not need an extra worker dependency
(eventlet/gevent) and so the existing Flask dev server / Gunicorn sync
worker keeps working. SocketIO falls back to HTTP long-polling for
transports that the server doesn't natively support, but the WS
handshake itself works.
"""

from flask_socketio import SocketIO, emit, join_room

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)


@socketio.on("connect", namespace="/monitoring")
def on_connect():
    emit("connected", {"message": "Connected to monitoring stream"})


@socketio.on("subscribe", namespace="/monitoring")
def on_subscribe(data):
    exam_id = (data or {}).get("exam_id")
    if not exam_id:
        emit("error", {"message": "exam_id required"})
        return
    join_room(f"exam:{exam_id}")
    emit("subscribed", {"exam_id": exam_id})


@socketio.on("subscribe_logs", namespace="/monitoring")
def on_subscribe_logs(_data=None):
    join_room("logs")
    emit("logs_subscribed", {"ok": True})


def emit_log_event(log_doc):
    """
    Push a freshly-written log doc to every WebSocket client subscribed to
    the "logs" room. Called by Module 13's write_log after insert so the
    teacher audit-logs UI updates in real time.
    """
    try:
        socketio.emit(
            "log_event",
            log_doc,
            to="logs",
            namespace="/monitoring",
        )
    except Exception:
        pass


def emit_monitoring_event(exam_id, kind, payload):
    """
    Push a monitoring event to every WebSocket client subscribed to the
    given exam's room. Called from Modules 10/11/12/15 after they record
    an event to their own collection.

    Safe to call even when there are no subscribers - the emit is a
    no-op in that case.
    """
    if not exam_id:
        return
    try:
        socketio.emit(
            kind,
            payload or {},
            to=f"exam:{exam_id}",
            namespace="/monitoring",
        )
    except Exception:
        # Never let a transport hiccup break the calling event-recording
        # path - monitoring events are best-effort relays.
        pass
