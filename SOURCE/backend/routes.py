"""
API route definitions for the notes service.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from sqlalchemy import select, func

from .agent import NotesAgent
from .auth import create_jwt, hash_password, verify_password
from .database import session_scope
from .models import Note, User
from .schemas import (
    LoginRequest,
    NLQueryRequest,
    NoteCreateRequest,
    NoteUpdateRequest,
    NoteResponse,
    RegisterRequest,
)


api_bp = Blueprint("api", __name__)
agent = NotesAgent()


def parse_request(model_cls, payload: Optional[dict] = None):
    """Utility to build and validate Pydantic models from request JSON."""
    payload = payload or request.get_json(silent=True) or {}
    return model_cls.model_validate(payload)


def serialize_note(note: Note, index: Optional[int] = None) -> Dict[str, Any]:
    data = NoteResponse.model_validate(note).model_dump()
    if index is not None:
        data["display_number"] = index
    return data


def current_user_id() -> int:
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid user identity in token") from exc


@api_bp.errorhandler(ValidationError)
def handle_validation_error(err: ValidationError):  # type: ignore[override]
    return jsonify({"error": "invalid-request", "details": err.errors()}), 400


@api_bp.route("/register", methods=["POST"])
def register_user():
    data = parse_request(RegisterRequest)
    with session_scope() as session:
        existing = session.execute(
            select(User).where(User.username == data.username)
        ).scalar_one_or_none()
        if existing:
            return jsonify({"error": "username-taken"}), 409

        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
        )
        session.add(user)
        session.flush()
        token = create_jwt(identity=user.user_id)
        return jsonify({"access_token": token, "user_id": user.user_id}), 201


@api_bp.route("/login", methods=["POST"])
def login_user():
    data = parse_request(LoginRequest)
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.username == data.username)
        ).scalar_one_or_none()
        if user is None or not verify_password(data.password, user.password_hash):
            return jsonify({"error": "invalid-credentials"}), 401

        user.touch_last_login()
        session.add(user)
        token = create_jwt(identity=user.user_id)
        return jsonify({"access_token": token, "user_id": user.user_id}), 200


@api_bp.route("/notes", methods=["GET"])
@jwt_required()
def list_notes():
    user_id = current_user_id()
    topic_filter = request.args.get("topic")
    with session_scope() as session:
        stmt = select(Note).where(Note.user_id == user_id)
        if topic_filter:
            stmt = stmt.where(Note.topic.ilike(f"%{topic_filter}%"))
        notes = session.execute(stmt.order_by(Note.note_id.asc())).scalars().all()
        serialized = [serialize_note(note, index=i + 1) for i, note in enumerate(notes)]
        return jsonify({"notes": serialized})


@api_bp.route("/notes", methods=["POST"])
@jwt_required()
def create_note():
    user_id = current_user_id()
    data = parse_request(NoteCreateRequest)
    with session_scope() as session:
        note = Note(
            user_id=user_id,
            topic=data.topic,
            message=data.message,
        )
        session.add(note)
        session.flush()
        count = session.execute(
            select(func.count()).select_from(Note).where(Note.user_id == user_id)
        ).scalar_one()
        return jsonify(serialize_note(note, index=count)), 201


@api_bp.route("/notes/<int:note_id>", methods=["PUT"])
@jwt_required()
def update_note(note_id: int):
    user_id = current_user_id()
    data = parse_request(NoteUpdateRequest)
    with session_scope() as session:
        note = session.execute(
            select(Note).where(Note.note_id == note_id, Note.user_id == user_id)
        ).scalar_one_or_none()
        if note is None:
            return jsonify({"error": "not-found"}), 404
        if data.topic is not None:
            note.topic = data.topic
        if data.message is not None:
            note.message = data.message
        session.add(note)
        return jsonify(serialize_note(note)), 200


@api_bp.route("/notes/<int:note_id>", methods=["DELETE"])
@jwt_required()
def delete_note(note_id: int):
    user_id = current_user_id()
    with session_scope() as session:
        note = session.execute(
            select(Note).where(Note.note_id == note_id, Note.user_id == user_id)
        ).scalar_one_or_none()
        if note is None:
            return jsonify({"error": "not-found"}), 404
        session.delete(note)
        return jsonify({"status": "deleted"}), 200


@api_bp.route("/nl-query", methods=["POST"])
@jwt_required()
def handle_nl_query():
    user_id = current_user_id()
    request_data = parse_request(NLQueryRequest)
    interpretation = agent.interpret(request_data.query)

    action = interpretation.action
    payload = interpretation.payload
    dry_run = request.args.get("dry_run") == "1"

    with session_scope() as session:
        if action == "create":
            topic = payload.get("topic") or "General"
            message = payload.get("message") or request_data.query
            note = Note(user_id=user_id, topic=topic, message=message)
            session.add(note)
            session.flush()
            result = serialize_note(note)
        elif action == "read":
            note = _resolve_note(session, user_id, payload)
            if not note:
                return jsonify({"error": "not-found"}), 404
            result = serialize_note(note)
        elif action == "update":
            note = _resolve_note(session, user_id, payload)
            if not note:
                return jsonify({"error": "not-found"}), 404
            if dry_run:
                return jsonify(
                    {
                        "action": action,
                        "agent_summary": payload.get("summary", ""),
                        "result": serialize_note(note),
                        "dry_run": True,
                    }
                )
            if payload.get("topic"):
                note.topic = payload["topic"]
            if payload.get("message"):
                note.message = payload["message"]
            session.add(note)
            result = serialize_note(note)
        elif action == "delete":
            note = _resolve_note(session, user_id, payload)
            if not note:
                return jsonify({"error": "not-found"}), 404
            if dry_run:
                return jsonify(
                    {
                        "action": action,
                        "agent_summary": payload.get("summary", ""),
                        "result": serialize_note(note),
                        "dry_run": True,
                    }
                )
            session.delete(note)
            result = {"status": "deleted", "note_id": note.note_id}
        else:  # list and fallback
            notes = session.execute(
                select(Note)
                .where(Note.user_id == user_id)
                .order_by(Note.last_update.desc())
            ).scalars()
            result = [serialize_note(note) for note in notes]

    return jsonify(
        {
            "action": action,
            "agent_summary": payload.get("summary", ""),
            "result": result,
            "dry_run": dry_run,
        }
    )


def _resolve_note(session, user_id: int, payload: Dict[str, Any]) -> Optional[Note]:
    """
    Resolve a note given a payload containing possible identifiers.
    """
    note_id = payload.get("note_id")
    topic_filter = payload.get("filters", {}).get("topic")

    stmt = select(Note).where(Note.user_id == user_id)
    if note_id:
        stmt = stmt.where(Note.note_id == note_id)
    elif topic_filter:
        stmt = stmt.where(Note.topic.ilike(f"%{topic_filter}%"))
    else:
        return None
    return session.execute(stmt).scalars().first()


__all__ = ["api_bp"]

