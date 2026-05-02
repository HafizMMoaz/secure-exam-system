def register_routes(app):
    from modules.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # from modules.session import session_bp
    # app.register_blueprint(session_bp, url_prefix="/api/session")

    # from modules.device import device_bp
    # app.register_blueprint(device_bp, url_prefix="/api/device")

    # from modules.activation import activation_bp
    # app.register_blueprint(activation_bp, url_prefix="/api/activation")

    # from modules.rbac import rbac_bp
    # app.register_blueprint(rbac_bp, url_prefix="/api/rbac")

    # from modules.questions import questions_bp
    # app.register_blueprint(questions_bp, url_prefix="/api/questions")

    # from modules.randomization import randomization_bp
    # app.register_blueprint(randomization_bp, url_prefix="/api/randomization")

    # from modules.timer import timer_bp
    # app.register_blueprint(timer_bp, url_prefix="/api/timer")

    # from modules.validation import validation_bp
    # app.register_blueprint(validation_bp, url_prefix="/api/validation")

    # from modules.tab import tab_bp
    # app.register_blueprint(tab_bp, url_prefix="/api/tab")

    # from modules.clipboard import clipboard_bp
    # app.register_blueprint(clipboard_bp, url_prefix="/api/clipboard")

    # from modules.activity import activity_bp
    # app.register_blueprint(activity_bp, url_prefix="/api/activity")

    # from modules.logging import logging_bp
    # app.register_blueprint(logging_bp, url_prefix="/api/logs")

    # from modules.multisession import multisession_bp
    # app.register_blueprint(multisession_bp, url_prefix="/api/multisession")

    # from modules.behavioral import behavioral_bp
    # app.register_blueprint(behavioral_bp, url_prefix="/api/behavioral")

    # from modules.similarity import similarity_bp
    # app.register_blueprint(similarity_bp, url_prefix="/api/similarity")

    # from modules.risk import risk_bp
    # app.register_blueprint(risk_bp, url_prefix="/api/risk")