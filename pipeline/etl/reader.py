"""
Load and deduplicate LiteLLM JSONL records.

LiteLLM logs one record per API request. Each record embeds the full
conversation history in its `messages` array, so naively reading all
records gives N copies of early messages. We deduplicate by sorting
requests within each session chronologically and keeping only the
net-new messages added by each successive request.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


# ── Agent normalization ────────────────────────────────────────────────────────

_AGENT_MAP = {
    "claude": "claude-code",
    "cursor": "claude-code",
    "copilot": "copilot",
    "github.copilot": "copilot",
    "opencode": "opencode",
    "chatgpt": "chatgpt",
    "gpt": "chatgpt",
}


def normalize_agent(raw: str | None) -> str:
    if not raw:
        return "other"
    low = raw.lower()
    for key, val in _AGENT_MAP.items():
        if key in low:
            return val
    return "other"


# ── Timestamp parsing ──────────────────────────────────────────────────────────

def parse_ts(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ── Message deduplication ──────────────────────────────────────────────────────

def message_fingerprint(msg: dict) -> str:
    """Stable hash of a message's role + content (first 512 chars for speed)."""
    role = msg.get("role", "")
    content = msg.get("content", "") or ""
    if isinstance(content, list):
        content = json.dumps(content, separators=(",", ":"))
    key = f"{role}:{str(content)[:512]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def deduplicate_messages(requests: list[dict]) -> list[tuple[dict, dict]]:
    """
    Given a list of raw request dicts for a single session (sorted by time),
    return a flat list of (message_dict, introducing_request_dict) pairs
    where each message appears exactly once.

    Strategy: track seen fingerprints; for each request take only messages
    whose fingerprint has not been seen yet.
    """
    seen: set[str] = set()
    result: list[tuple[dict, dict]] = []
    for req in requests:
        messages = req.get("messages") or []
        for msg in messages:
            fp = message_fingerprint(msg)
            if fp not in seen:
                seen.add(fp)
                result.append((msg, req))
    return result


# ── Group raw records by session ───────────────────────────────────────────────

def group_by_session(records: list[dict]) -> dict[str, list[dict]]:
    sessions: dict[str, list[dict]] = {}
    for rec in records:
        metadata = rec.get("metadata") or {}
        session_id = (
            metadata.get("session_id")
            or metadata.get("tags", {}).get("session_id")
            or rec.get("session_id")
            or "unknown"
        )
        sessions.setdefault(session_id, []).append(rec)
    # sort each session's requests chronologically
    for sid in sessions:
        sessions[sid].sort(key=lambda r: parse_ts(r.get("startTime") or r.get("start_time") or 0))
    return sessions


# ── Extract tool definitions ───────────────────────────────────────────────────

def extract_tool_definitions(records: list[dict]) -> list[dict]:
    """Return unique tool definitions across all records (deduplicated by hash)."""
    seen: set[str] = set()
    result: list[dict] = []
    for rec in records:
        for tool in rec.get("tools") or []:
            fn = tool.get("function") or tool
            canonical = json.dumps(fn, sort_keys=True, separators=(",", ":"))
            tool_hash = hashlib.sha256(canonical.encode()).hexdigest()[:32]
            if tool_hash not in seen:
                seen.add(tool_hash)
                result.append({
                    "tool_hash": tool_hash,
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": json.dumps(fn.get("parameters") or fn.get("input_schema") or {}),
                    "raw_record": rec,
                })
    return result


# ── Token estimation ───────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(str(text)) // 4)
