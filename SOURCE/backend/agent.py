"""
Natural language agent that translates user intent to CRUD actions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .config import get_settings


settings = get_settings()


SYSTEM_PROMPT = """
You are an assistant for a notes management system. Interpret the user's
request and respond with a JSON object describing the necessary action.

You must ALWAYS return a JSON object with this schema:
{
  "action": "create" | "read" | "update" | "delete" | "list",
  "topic": string | null,
  "message": string | null,
  "note_id": int | null,
  "filters": { "topic": string | null },
  "summary": string
}

Rules:
- "create" requires topic and message.
- "read" retrieves a single note; include note_id or topic filter.
- "update" requires note_id or topic filter, plus message and/or topic.
- "delete" requires note_id or topic filter.
- "list" returns a list of notes (ignore topic/message unless they narrow results).
- Use summary to briefly explain what you understood.
- If information is missing, choose the best guess and explain uncertainty in summary.
- Note IDs are integers. If user mentions 'note 2', set note_id to 2.
- Topic comparisons are case-insensitive.
- For queries like "What did I say about X", use read action with topic filter.
- For general overviews like "Show all notes", use list.
- If user asks to update by topic name and multiple matches could exist,
  still proceed and explain ambiguity in summary.
"""


@dataclass
class AgentResult:
    action: str
    payload: Dict[str, Any]


class NotesAgent:
    """
    Simple agent that delegates intent parsing to an Ollama-compatible LLM.

    The agent falls back to deterministic keyword matching if the LLM service
    is unreachable so that basic functionality remains testable.
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.llm_timeout_seconds

    def interpret(self, user_query: str) -> AgentResult:
        try:
            response_json = self._query_llm(user_query)
            return AgentResult(
                action=response_json.get("action", "list"),
                payload=response_json,
            )
        except Exception:
            fallback = self._fallback_parse(user_query)
            return AgentResult(action=fallback.get("action", "list"), payload=fallback)

    def _query_llm(self, user_query: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": user_query,
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("response") or data.get("message", {}).get("content", "")
        return json.loads(content)

    def _extract_note_id(self, text: str) -> Optional[int]:
        match = re.search(r"note[\s#-]*(\d+)", text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _fallback_parse(self, user_query: str) -> Dict[str, Any]:
        lowered = user_query.lower()
        note_id = self._extract_note_id(lowered)

        result: Dict[str, Any] = {
            "action": "list",
            "topic": None,
            "message": None,
            "note_id": note_id,
            "filters": {"topic": None},
            "summary": "Fallback keyword interpretation; please verify intent.",
        }

        if any(word in lowered for word in ["create", "add", "new", "remember"]):
            result["action"] = "create"
            if " about " in lowered:
                topic = user_query.split(" about ", 1)[1].strip().capitalize()
                result["topic"] = topic
                result["message"] = f"Reminder about {topic}"
            else:
                result["topic"] = "General"
                result["message"] = user_query
            result["summary"] = "Created note using heuristic."
        elif any(word in lowered for word in ["update", "change", "edit"]):
            result["action"] = "update"
            result["summary"] = (
                f"Update note heuristic for note {note_id}."
                if note_id
                else "Update note heuristic; please specify details."
            )
        elif any(word in lowered for word in ["delete", "remove", "clear", "trash"]):
            result["action"] = "delete"
            result["summary"] = (
                f"Delete note heuristic for note {note_id}."
                if note_id
                else "Delete note heuristic; please confirm details."
            )
        elif any(word in lowered for word in ["show", "view", "read", "detail"]):
            result["action"] = "read" if note_id else "list"
            result["summary"] = (
                f"Read note heuristic for note {note_id}."
                if note_id
                else "Listing notes."
            )
        elif any(word in lowered for word in ["list", "all", "display"]):
            result["action"] = "list"
            result["summary"] = "Listing notes."

        return result


__all__ = ["NotesAgent", "AgentResult"]

