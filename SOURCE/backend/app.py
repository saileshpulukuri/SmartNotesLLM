"""
Flask application factory for the notes backend.
"""

from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import get_settings
from .database import engine
from .models import Base
from .routes import api_bp


def create_app() -> Flask:
    settings = get_settings()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["JWT_SECRET_KEY"] = settings.jwt_secret_key

    CORS(app)
    jwt = JWTManager(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):  # type: ignore[override]
        return jsonify({"error": "token-expired"}), 401

    Base.metadata.create_all(bind=engine)

    app.register_blueprint(api_bp, url_prefix=settings.api_prefix)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


__all__ = ["create_app"]

