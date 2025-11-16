"""
Streamlit frontend for the CS5200 notes management assignment.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")
API_PREFIX = os.getenv("API_PREFIX", "/api")


def api_url(path: str) -> str:
    return f"{BACKEND_URL.rstrip('/')}{API_PREFIX}{path}"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        /* Flash message styling with fade-out animation */
        .flash-message {
            padding: 0.9rem 1.2rem;
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
            font-weight: 500;
            animation: flash-fade 10s forwards;
        }
        .flash-success {
            background-color: rgba(46, 204, 113, 0.2);
            color: #2ecc71;
        }
        .flash-error {
            background-color: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
        }
        .flash-info {
            background-color: rgba(52, 152, 219, 0.2);
            color: #3498db;
        }
        @keyframes flash-fade {
            0%, 90% { opacity: 1; }
            100% { opacity: 0; display: none; }
        }

        /* Auth form sizing */
        .auth-wrapper {
            max-width: 420px;
            margin: 0 auto;
        }
        .auth-wrapper button {
            width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_json_response(response: requests.Response) -> Dict[str, Any]:
    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            body = response.text or response.reason or "Unknown error"
            error_payload = {
                "error": body,
                "details": {
                    "status": response.status_code,
                    "url": str(response.url),
                },
            }
        raise RuntimeError(error_payload)

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid JSON response: {exc}. Body: {response.text!r}"
        ) from exc


def post_json(path: str, payload: Dict[str, Any], token: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(api_url(path), json=payload, headers=headers, timeout=30)
    return _ensure_json_response(response)


def put_json(path: str, payload: Dict[str, Any], token: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.put(api_url(path), json=payload, headers=headers, timeout=30)
    return _ensure_json_response(response)


def delete_json(path: str, token: Optional[str] = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.delete(api_url(path), headers=headers, timeout=30)
    return _ensure_json_response(response)


def get_json(path: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(api_url(path), params=params or {}, headers=headers, timeout=30)
    return _ensure_json_response(response)


def _summarize_exception(error: Exception, context: str) -> Tuple[str, Optional[str]]:
    message = None
    details = None

    if hasattr(error, "args") and error.args:
        first_arg = error.args[0]
        if isinstance(first_arg, dict):
            message = first_arg.get("error") or first_arg.get("message")
            detail_payload = first_arg.get("details")
            if isinstance(detail_payload, dict):
                details = ", ".join(f"{k}: {v}" for k, v in detail_payload.items())
            elif isinstance(detail_payload, list):
                detail_messages = []
                for entry in detail_payload:
                    if isinstance(entry, dict):
                        loc = entry.get("loc") or []
                        if isinstance(loc, (list, tuple)):
                            loc = ".".join(str(part) for part in loc)
                        msg = entry.get("msg")
                        if msg:
                            detail_messages.append(f"{loc}: {msg}" if loc else msg)
                if detail_messages:
                    details = "; ".join(detail_messages)
        elif isinstance(first_arg, str):
            message = first_arg

    if not message:
        message = str(error)

    return f"{context}: {message}", details


def render_error_dialog(error: Exception, context: str) -> None:
    text, detail = _summarize_exception(error, context)
    st.error(text)
    if detail:
        st.caption(detail)


def extract_note_from_result(result: Any) -> Optional[Dict[str, Any]]:
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            return first
    return None


def describe_agent_result(action: str, result: Any) -> str:
    note = extract_note_from_result(result)
    if action == "create" and note:
        topic = note.get("topic") or "Untitled"
        message = note.get("message") or ""
        return f"Created a note titled “{topic}” with message “{message}”."
    if action == "update" and note:
        return f"Updated note “{note.get('topic', 'Untitled')}”."
    if action == "delete" and isinstance(result, dict):
        return f"Deleted note #{result.get('note_id', '')}."
    if action == "read" and note:
        return f"Retrieved note “{note.get('topic', 'Untitled')}”: {note.get('message','')}"
    if action == "list" and isinstance(result, list):
        return f"Listed {len(result)} notes."
    return "Action completed."


def mark_note_pending_details(note: Dict[str, Any]) -> None:
    st.session_state["pending_note_details"] = {
        "note_id": note.get("note_id"),
        "display_number": note.get("display_number"),
        "topic": note.get("topic") or "",
        "message": note.get("message") or "",
    }


def migrate_history_entries() -> None:
    history: List[Dict[str, Any]] = st.session_state["query_history"]
    for idx, entry in enumerate(history):
        if "assistant" not in entry and "response" in entry:
            response = entry.get("response") or {}
            summary = describe_agent_result(
                response.get("action", ""), response.get("result")
            )
            history[idx] = {
                "query": entry.get("query", ""),
                "assistant": summary,
            }


NOTE_PATTERN = re.compile(r"note[\s#-]*(\d+)")


def extract_note_id_from_text(text: str) -> Optional[int]:
    match = NOTE_PATTERN.search(text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def append_history_entry(query_text: Optional[str], assistant_text: str) -> None:
    st.session_state["query_history"].append(
        {"query": query_text or "", "assistant": assistant_text}
    )


def find_note_by_title(text: str, notes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    text = text.lower()
    # Exact match first
    for note in notes:
        if note.get("topic", "").lower() == text.strip():
            return note
    # Contains match
    for note in notes:
        topic = note.get("topic", "").lower()
        if topic and topic in text:
            return note
    return None


def ensure_session_defaults() -> None:
    defaults = {
        "token": None,
        "user_id": None,
        "username": None,
        "auth_stage": "login",
        "query_history": [],
        "flash": None,
        "show_create_form": False,
        "editing_note_id": None,
        "view_note_id": None,
        "confirm_delete_id": None,
        "search_term": "",
        "manual_mode": False,
        "pending_note_details": None,
        "pending_edit_note": None,
        "pending_delete_note": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_flash(level: str, message: str) -> None:
    st.session_state["flash"] = (level, message)


def set_error_flash(context: str, error: Exception) -> None:
    text, detail = _summarize_exception(error, context)
    if detail:
        text = f"{text} ({detail})"
    set_flash("error", text)


def pop_flash() -> Optional[Tuple[str, str]]:
    flash = st.session_state.get("flash")
    st.session_state["flash"] = None
    return flash


def switch_stage(stage: str, flash: Optional[Tuple[str, str]] = None) -> None:
    st.session_state["auth_stage"] = stage
    if flash:
        set_flash(*flash)
    st.rerun()


def logout() -> None:
    st.session_state["token"] = None
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.session_state["query_history"] = []
    switch_stage("login", ("info", "You have been logged out."))


def display_flash() -> None:
    flash = pop_flash()
    if not flash:
        return

    placeholder = st.empty()
    level, message = flash
    css_class = {
        "success": "flash-success",
        "error": "flash-error",
        "warning": "flash-error",
        "info": "flash-info",
    }.get(level, "flash-info")
    placeholder.markdown(
        f"<div class='flash-message {css_class}'>{message}</div>",
        unsafe_allow_html=True,
    )


def render_login() -> None:
    st.header("Welcome back")
    st.markdown("Sign in to manage your personal notes with natural language.")

    login_col_left, login_col_center, login_col_right = st.columns([1, 2, 1])
    with login_col_center:
        with st.container():
            st.markdown("<div class='auth-wrapper'>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Log in")
                if submitted:
                    try:
                        data = post_json("/login", {"username": username, "password": password})
                        st.session_state["token"] = data["access_token"]
                        st.session_state["user_id"] = data["user_id"]
                        st.session_state["username"] = username
                        switch_stage("dashboard", ("success", "Login successful."))
                    except Exception as exc:
                        set_error_flash("Login failed", exc)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.write("Don't have an account?")
    if st.button("Create a new account"):
        switch_stage("register")


def render_register() -> None:
    st.header("Create a new account")
    st.markdown("Fill in the details below to register and start taking notes.")

    reg_col_left, reg_col_center, reg_col_right = st.columns([1, 2, 1])
    with reg_col_center:
        with st.container():
            st.markdown("<div class='auth-wrapper'>", unsafe_allow_html=True)
            with st.form("register_form"):
                username = st.text_input("Username", key="register_username")
                password = st.text_input("Password", type="password", key="register_password")
                confirm = st.text_input("Confirm password", type="password", key="register_confirm")
                submitted = st.form_submit_button("Register")
                if submitted:
                    if not username or not password:
                        set_flash("error", "Username and password are required.")
                        st.rerun()
                    elif password != confirm:
                        set_flash("error", "Passwords do not match.")
                        st.rerun()
                    else:
                        try:
                            post_json(
                                "/register",
                                {"username": username, "password": password},
                            )
                            st.session_state["username"] = username
                            switch_stage(
                                "login",
                                ("success", "Account created successfully. Please log in."),
                            )
                        except Exception as exc:
                            set_error_flash("Registration failed", exc)
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.write("Already have an account?")
    if st.button("Back to login"):
        switch_stage("login")


def render_notes_dashboard(token: str):
    st.header("Personal Notes Assistant")
    top_cols = st.columns([6, 1])
    with top_cols[-1]:
        if st.button("Log out", use_container_width=True):
            logout()
            st.stop()

    st.caption("Use the AI assistant for natural-language CRUD. Enable manual entries only if you need to override the agent.")

    notes: List[Dict[str, Any]] = []
    notes_error: Optional[Exception] = None
    try:
        notes = get_json("/notes", token=token)["notes"]
    except Exception as exc:
        notes_error = exc
    note_lookup = {note["note_id"]: note for note in notes}
    display_to_id: Dict[int, int] = {}
    for note in notes:
        dn = note.get("display_number")
        if isinstance(dn, int):
            display_to_id[dn] = note["note_id"]

    st.write("")
    st.subheader("Notes")
    previous_manual_mode = st.session_state.get("manual_mode", False)
    manual_mode = st.toggle(
        "Manual entries",
        value=st.session_state.get("manual_mode", False),
        help="Turn on to reveal buttons for manual CRUD changes.",
    )
    st.session_state["manual_mode"] = manual_mode
    migrate_history_entries()
    if previous_manual_mode and not manual_mode:
        st.session_state["show_create_form"] = False
        st.session_state["editing_note_id"] = None
        st.session_state["view_note_id"] = None
        st.session_state["confirm_delete_id"] = None

    if notes:
        search_term = st.text_input(
            "Search notes",
            value=st.session_state.get("search_term", ""),
            placeholder="Search by title or message…",
        )
    else:
        search_term = ""
    st.session_state["search_term"] = search_term

    username = st.session_state.get("username") or "You"

    if manual_mode:
        if st.button("➕ Add new note", key="toggle_create"):
            st.session_state["show_create_form"] = not st.session_state["show_create_form"]
            st.session_state["editing_note_id"] = None
            st.session_state["view_note_id"] = None
            st.session_state["confirm_delete_id"] = None
            st.rerun()

        if st.session_state.get("show_create_form"):
            with st.form("inline_create_form"):
                topic = st.text_input("Title", key="inline_create_topic")
                message = st.text_area("Description", key="inline_create_message")
                submitted = st.form_submit_button("Save note")
                if submitted:
                    if not topic or not message:
                        st.warning("Both title and description are required.")
                    else:
                        try:
                            post_json("/notes", {"topic": topic, "message": message}, token=token)
                            set_flash("success", "Note created.")
                            st.session_state["show_create_form"] = False
                            st.rerun()
                        except Exception as exc:
                            render_error_dialog(exc, "Could not create note")
            st.divider()

    filtered_notes = notes
    if search_term.strip():
        lowered = search_term.lower()
        filtered_notes = [
            note
            for note in notes
            if lowered in note["topic"].lower() or lowered in note["message"].lower()
        ]

    if manual_mode:
        header_cols = st.columns([1, 2, 3, 2, 2, 0.6, 0.6, 0.6])
    else:
        header_cols = st.columns([1, 2, 3, 2, 2])
    header_cols[0].markdown("**#**")
    header_cols[1].markdown("**Title**")
    header_cols[2].markdown("**Description**")
    header_cols[3].markdown("**Created By**")
    header_cols[4].markdown("**Last Updated**")
    if manual_mode:
        header_cols[5].markdown("**View**")
        header_cols[6].markdown("**Edit**")
        header_cols[7].markdown("**Delete**")

    if notes_error:
        render_error_dialog(notes_error, "Unable to load notes")
    elif not filtered_notes:
        if search_term.strip():
            st.info("No notes match your search. Try a different keyword.")
        else:
            st.info("No notes yet. Create a new one to get started.")
    else:
        for note in filtered_notes:
            display_number = note.get("display_number", note["note_id"])
            cols = st.columns([1, 2, 3, 2, 2] + ([0.6, 0.6, 0.6] if manual_mode else []))
            cols[0].write(f"#{display_number}")
            cols[1].write(note["topic"])
            cols[2].write(note["message"][:120] + ("…" if len(note["message"]) > 120 else ""))
            cols[3].write(username)
            cols[4].write(note["last_update"])
            if manual_mode:
                if cols[5].button("👁️", key=f"view_{note['note_id']}"):
                    st.session_state["view_note_id"] = note["note_id"]
                    st.session_state["editing_note_id"] = None
                if cols[6].button("✏️", key=f"edit_{note['note_id']}"):
                    st.session_state["editing_note_id"] = note["note_id"]
                    st.session_state["view_note_id"] = None
                if cols[7].button("🗑️", key=f"delete_{note['note_id']}"):
                    st.session_state["confirm_delete_id"] = note["note_id"]
                    st.session_state["view_note_id"] = None
                    st.session_state["editing_note_id"] = None
            st.divider()

    if manual_mode:
        edit_id = st.session_state.get("editing_note_id")
        if edit_id:
            note = next((n for n in notes if n["note_id"] == edit_id), None)
            if note:
                display_number = note.get("display_number", edit_id)
                st.subheader(f"Edit note #{display_number}")
                with st.form("edit_note_form"):
                    topic = st.text_input("Title", value=note["topic"], key=f"edit_topic_{edit_id}")
                    message = st.text_area("Description", value=note["message"], key=f"edit_message_{edit_id}")
                    submitted = st.form_submit_button("Save changes")
                    if submitted:
                        payload = {}
                        if topic != note["topic"]:
                            payload["topic"] = topic
                        if message != note["message"]:
                            payload["message"] = message
                        if not payload:
                            st.info("No changes detected.")
                        else:
                            try:
                                put_json(f"/notes/{edit_id}", payload, token=token)
                                set_flash("success", "Note updated.")
                                st.session_state["editing_note_id"] = None
                                st.rerun()
                            except Exception as exc:
                                render_error_dialog(exc, "Could not update note")

        view_id = st.session_state.get("view_note_id")
        if view_id:
            note = next((n for n in notes if n["note_id"] == view_id), None)
            if note:
                display_number = note.get("display_number", view_id)
                st.subheader(f"Viewing note #{display_number}")
                st.markdown(f"**Title:** {note['topic']}")
                st.markdown(f"**Description:** {note['message']}")
                st.caption(f"Last updated: {note['last_update']}")
                if st.button("Close viewer", key="close_viewer"):
                    st.session_state["view_note_id"] = None
                    st.rerun()

        confirm_id = st.session_state.get("confirm_delete_id")
        if confirm_id:
            note = next((n for n in notes if n["note_id"] == confirm_id), None)
            if note:
                display_number = note.get("display_number", confirm_id)
                st.warning(f"Delete note #{display_number} – “{note['topic']}”?")
                confirm_cols = st.columns([1, 1])
                if confirm_cols[0].button("Yes, delete", key="confirm_delete_yes"):
                    try:
                        delete_json(f"/notes/{confirm_id}", token=token)
                        set_flash("success", "Note deleted.")
                        st.session_state["confirm_delete_id"] = None
                        st.rerun()
                    except Exception as exc:
                        render_error_dialog(exc, "Could not delete note")
                if confirm_cols[1].button("No, keep it", key="confirm_delete_no"):
                    st.session_state["confirm_delete_id"] = None
                    st.rerun()

    # LLM-driven follow-ups
    pending_edit = st.session_state.get("pending_edit_note")
    if pending_edit:
        display_number = pending_edit.get("display_number") or pending_edit.get("note_id")
        st.subheader(f"Assistant edit for note #{display_number}")
        with st.form("llm_edit_note_form"):
            topic = st.text_input("Title", value=pending_edit.get("topic", ""))
            message = st.text_area("Description", value=pending_edit.get("message", ""))
            cols = st.columns([1, 1])
            submitted = cols[0].form_submit_button("Update note")
            skip = cols[1].form_submit_button("Skip")
        if submitted:
            payload: Dict[str, Any] = {}
            if topic != pending_edit.get("topic"):
                payload["topic"] = topic
            if message != pending_edit.get("message"):
                payload["message"] = message
            if payload:
                try:
                    put_json(f"/notes/{pending_edit['note_id']}", payload, token=token)
                    set_flash("success", "Note updated with new details.")
                    st.session_state["pending_edit_note"] = None
                    st.rerun()
                except Exception as exc:
                    render_error_dialog(exc, "Could not update note")
            else:
                st.info("No changes detected.")
        if not submitted and skip:
            st.session_state["pending_edit_note"] = None
            st.rerun()

    pending_delete = st.session_state.get("pending_delete_note")
    if pending_delete:
        display_number = pending_delete.get("display_number") or pending_delete.get("note_id")
        st.warning(f"Undo delete for note #{display_number} – “{pending_delete.get('topic','')}”?")
        cols = st.columns([1, 1])
        restore = cols[0].button("Restore note", key="pending_delete_restore")
        keep = cols[1].button("Keep deleted", key="pending_delete_keep")
        if restore:
            try:
                post_json(
                    "/notes",
                    {
                        "topic": pending_delete.get("topic", "Restored note"),
                        "message": pending_delete.get("message", ""),
                    },
                    token=token,
                )
                set_flash("success", "Note restored.")
            except Exception as exc:
                render_error_dialog(exc, "Could not restore note")
            finally:
                st.session_state["pending_delete_note"] = None
                st.experimental_rerun()
        if keep:
            st.session_state["pending_delete_note"] = None
            set_flash("info", "Deletion kept.")
            st.rerun()

    st.divider()
    st.subheader("Ask the AI Assistant")
    st.caption("Press Enter or click Send to submit your request.")

    with st.form(key="nl_query_form", clear_on_submit=True):
        input_col, button_col = st.columns([6, 1])
        with input_col:
            query = st.text_input(
                "Enter your request",
                placeholder="e.g., Create a new note reminding me to pay rent",
                label_visibility="collapsed",
            )
        with button_col:
            submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted and query.strip():
            query_lower = query.lower()
            requested_display_number = extract_note_id_from_text(query_lower)
            matched_note = None
            matched_display_number: Optional[int] = None
            handled_request = False

            if requested_display_number and requested_display_number in display_to_id:
                note_id_for_display = display_to_id[requested_display_number]
                matched_note = note_lookup.get(note_id_for_display)
                matched_display_number = requested_display_number
            else:
                title_match = find_note_by_title(query_lower, notes)
                if title_match:
                    matched_note = title_match
                    matched_display_number = title_match.get("display_number")

            # 1) Explicit delete via note number/title
            if any(k in query_lower for k in ["delete", "remove", "trash", "clear"]):
                handled_request = True
                if matched_note and matched_display_number is not None:
                    st.session_state["pending_delete_note"] = matched_note
                    assistant_text = (
                        f"Do you want me to delete note #{matched_display_number} "
                        f"titled “{matched_note.get('topic','Untitled')}”?"
                    )
                    append_history_entry(query, assistant_text)
                else:
                    append_history_entry(query, "I couldn't find that note to delete.")

            # 2) Explicit edit via note number/title
            if any(k in query_lower for k in ["edit", "update", "change"]):
                handled_request = True
                if matched_note and matched_display_number is not None:
                    st.session_state["pending_edit_note"] = matched_note
                    assistant_text = (
                        f"Let's update note #{matched_display_number}. "
                        "Use the form below to provide the new title and description."
                    )
                    append_history_entry(query, assistant_text)
                else:
                    append_history_entry(query, "I couldn't find that note to edit.")

            # 3) View note contents by number/title
            if any(k in query_lower for k in ["view", "show", "content", "read"]) and matched_note:
                handled_request = True
                desc = (
                    f"Note #{matched_note.get('display_number', matched_display_number or '')} – "
                    f"{matched_note.get('topic','Untitled')}: {matched_note.get('message','')}\n"
                    "Note retrieved successfully."
                )
                append_history_entry(query, desc)

            # 4) Fallback to LLM endpoint for create/list/general queries
            if not handled_request:
                try:
                    response = post_json("/nl-query", {"query": query}, token=token)
                    action = response.get("action", "")
                    result = response.get("result")
                    description = describe_agent_result(action, result)
                    append_history_entry(query, description)

                    if action == "create":
                        note = extract_note_from_result(result)
                        if note:
                            mark_note_pending_details(note)
                            st.info(
                                "Note created. Add a specific title and description below?"
                            )
                except Exception as exc:
                    msg, detail = _summarize_exception(exc, "Could not process query")
                    append_history_entry(query, msg if not detail else f"{msg} ({detail})")
                    render_error_dialog(exc, "Could not process query")

    st.subheader("Conversation")
    history = st.session_state["query_history"]
    if not history:
        st.caption("No questions asked yet.")
    else:
        for entry in history:
            query_text = entry.get("query", "")
            if query_text:
                with st.chat_message("user"):
                    st.write(query_text)
            with st.chat_message("assistant"):
                st.write(entry.get("assistant", ""))

    pending = st.session_state.get("pending_note_details")
    if pending and pending.get("note_id"):
        display_number = pending.get("display_number") or pending.get("note_id")
        st.info(
            f"Note #{display_number} was created with placeholder text. "
            "Add a title and description?"
        )
        with st.form("pending_details_form"):
            pending_title = st.text_input("Title", value=pending.get("topic", ""))
            pending_message = st.text_area(
                "Description", value=pending.get("message", "")
            )
            cols = st.columns([1, 1])
            submitted = cols[0].form_submit_button("Save details")
            skip = cols[1].form_submit_button("Skip")
        if submitted:
            try:
                put_json(
                    f"/notes/{pending['note_id']}",
                    {"topic": pending_title, "message": pending_message},
                    token=token,
                )
                st.session_state["pending_note_details"] = None
                set_flash("success", "Note updated with your details.")
                st.rerun()
            except Exception as exc:
                render_error_dialog(exc, "Could not update newly created note")
        if not submitted and skip:
            st.session_state["pending_note_details"] = None
            st.rerun()

    pending_edit = st.session_state.get("pending_edit_note")
    if pending_edit and pending_edit.get("note_id"):
        display_number = pending_edit.get("display_number") or pending_edit.get("note_id")
        st.info(f"Provide updates for note #{display_number}.")
        with st.form("pending_edit_form"):
            new_title = st.text_input("New title", value=pending_edit.get("topic", ""))
            new_message = st.text_area(
                "New description", value=pending_edit.get("message", "")
            )
            cols = st.columns([1, 1])
            submitted = cols[0].form_submit_button("Apply changes")
            skip = cols[1].form_submit_button("Cancel")
        if submitted:
            payload: Dict[str, Any] = {}
            if new_title != pending_edit.get("topic"):
                payload["topic"] = new_title
            if new_message != pending_edit.get("message"):
                payload["message"] = new_message
            if payload:
                try:
                    put_json(f"/notes/{pending_edit['note_id']}", payload, token=token)
                    append_history_entry(
                        None,
                        f"Updated note #{display_number} successfully.",
                    )
                    st.session_state["pending_edit_note"] = None
                    set_flash("success", "Note updated.")
                    st.rerun()
                except Exception as exc:
                    render_error_dialog(exc, "Could not update note")
            else:
                set_flash("info", "No changes detected.")
                st.rerun()
        if not submitted and skip:
            st.session_state["pending_edit_note"] = None
            set_flash("info", "Edit cancelled.")
            st.rerun()

    pending_delete = st.session_state.get("pending_delete_note")
    if pending_delete and pending_delete.get("note_id"):
        display_number = pending_delete.get("display_number") or pending_delete.get("note_id")
        st.warning(
            f"Delete note #{display_number} titled “{pending_delete.get('topic','Untitled')}”?"
        )
        cols = st.columns([1, 1])
        confirm = cols[0].button("Yes, delete it", key="pending_delete_yes")
        cancel = cols[1].button("No, keep it", key="pending_delete_no")
        if confirm:
            try:
                delete_json(f"/notes/{pending_delete['note_id']}", token=token)
                append_history_entry(
                    None,
                    f"Deleted note #{display_number}.",
                )
                st.session_state["pending_delete_note"] = None
                set_flash("success", "Note deleted.")
                st.rerun()
            except Exception as exc:
                render_error_dialog(exc, "Could not delete note")
        if cancel:
            append_history_entry(
                None, "Okay, I won't delete that note."
            )
            st.session_state["pending_delete_note"] = None
            st.rerun()

    st.subheader("All Notes")
    if notes_error:
        render_error_dialog(notes_error, "Unable to load notes")
    elif not notes:
        st.info("No notes yet. Create one above to get started.")
    else:
        for note in notes:
            st.markdown(f"### {note['topic']}")
            st.write(note["message"])
            st.caption(f"Last update: {note['last_update']}")


def main():
    st.set_page_config(page_title="CS5200 Notes Assistant", page_icon="📝", layout="wide")
    ensure_session_defaults()
    inject_styles()

    display_flash()

    stage = st.session_state["auth_stage"]
    token = st.session_state.get("token")

    if stage == "dashboard" and token:
        render_notes_dashboard(token)
    elif stage == "register":
        render_register()
    else:
        render_login()


if __name__ == "__main__":
    main()

