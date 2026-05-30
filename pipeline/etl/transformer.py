"""
Transform grouped session data into the five output tables.
Returns lists of dataclass instances ready for Parquet serialization.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from .models import Message, ModelResponse, Session, ToolCall, ToolDefinition
from .reader import (
    deduplicate_messages,
    estimate_tokens,
    extract_tool_definitions,
    normalize_agent,
    parse_ts,
)


def _message_id(session_id: str, turn_index: int, role: str, content: str) -> str:
    key = f"{session_id}:{turn_index}:{role}:{str(content)[:256]}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _content_str(content: Any) -> str:
    if isinstance(content, str):
        return content[:10_000]
    if isinstance(content, list):
        return json.dumps(content, separators=(",", ":"))[:10_000]
    return str(content or "")[:10_000]


def _extract_user_id(metadata: dict) -> str:
    return (
        metadata.get("user_api_key_alias")
        or metadata.get("user")
        or metadata.get("user_api_key_user_id")
        or metadata.get("user_api_key_hash", "")[:12]
        or "unknown"
    )


def _extract_team(metadata: dict) -> str:
    return (
        metadata.get("team_alias")
        or metadata.get("team_id", "")[:12]
        or metadata.get("tags", {}).get("team", "")
        or "unknown"
    )


def _extract_agent(req: dict, metadata: dict) -> str:
    raw = (
        metadata.get("user_agent")
        or metadata.get("tags", {}).get("agent")
        or req.get("user_agent")
        or req.get("proxy_server_request", {}).get("headers", {}).get("user-agent", "")
    )
    return normalize_agent(raw)


def _primary_model(requests: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in requests:
        m = r.get("model") or r.get("kwargs", {}).get("model", "unknown")
        counts[m] = counts.get(m, 0) + 1
    return max(counts, key=counts.get) if counts else "unknown"


# ── Main transform ─────────────────────────────────────────────────────────────

def transform_sessions(
    sessions: dict[str, list[dict]],
    partition_date: date,
) -> tuple[
    list[Session],
    list[Message],
    list[ToolCall],
    list[ModelResponse],
    list[ToolDefinition],
]:
    all_sessions: list[Session] = []
    all_messages: list[Message] = []
    all_tool_calls: list[ToolCall] = []
    all_model_responses: list[ModelResponse] = []
    tool_def_map: dict[str, ToolDefinition] = {}

    # Extract tool definitions from all records across all sessions
    all_records = [r for reqs in sessions.values() for r in reqs]
    for td_raw in extract_tool_definitions(all_records):
        ts = parse_ts(td_raw["raw_record"].get("startTime") or 0)
        td = ToolDefinition(
            tool_hash=td_raw["tool_hash"],
            name=td_raw["name"],
            description=td_raw["description"],
            input_schema=td_raw["input_schema"],
            first_seen=ts,
        )
        if td.tool_hash not in tool_def_map:
            tool_def_map[td.tool_hash] = td

    for session_id, requests in sessions.items():
        if not requests:
            continue

        first_req = requests[0]
        last_req = requests[-1]
        metadata = first_req.get("metadata") or {}
        user_id = _extract_user_id(metadata)
        team = _extract_team(metadata)
        agent = _extract_agent(first_req, metadata)
        model = _primary_model(requests)
        start_time = parse_ts(first_req.get("startTime") or first_req.get("start_time") or 0)
        end_time = parse_ts(last_req.get("endTime") or last_req.get("end_time") or last_req.get("startTime") or 0)

        total_input = 0
        total_output = 0
        total_cost = 0.0
        session_turn_base = 0

        # Build model_responses (one per request)
        for req in requests:
            req_id = req.get("id") or req.get("litellm_call_id") or "unknown"
            usage = req.get("usage") or {}
            resp_meta = req.get("metadata") or {}
            ts = parse_ts(req.get("startTime") or req.get("start_time") or 0)
            inp = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            cache_read = int(
                usage.get("cache_read_input_tokens")
                or usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
                or 0
            )
            cost = float(resp_meta.get("spend") or req.get("response_cost") or 0.0)
            latency = int(resp_meta.get("response_time") or req.get("response_ms") or 0)
            choices = req.get("choices") or []
            stop_reason = choices[0].get("finish_reason", "") if choices else ""

            total_input += inp
            total_output += out
            total_cost += cost

            all_model_responses.append(ModelResponse(
                request_id=req_id,
                session_id=session_id,
                model=req.get("model") or "unknown",
                input_tokens=inp,
                output_tokens=out,
                cache_read_tokens=cache_read,
                cost_usd=cost,
                latency_ms=latency,
                stop_reason=stop_reason,
                timestamp=ts,
                date=partition_date,
            ))

        # Deduplicate messages across requests
        deduped = deduplicate_messages(requests)
        for turn_index, (msg, introducing_req) in enumerate(deduped):
            req_id = introducing_req.get("id") or introducing_req.get("litellm_call_id") or "unknown"
            ts = parse_ts(introducing_req.get("startTime") or introducing_req.get("start_time") or 0)
            role = msg.get("role", "unknown")
            content = _content_str(msg.get("content"))
            msg_id = _message_id(session_id, turn_index, role, content)

            all_messages.append(Message(
                message_id=msg_id,
                session_id=session_id,
                request_id=req_id,
                turn_index=turn_index,
                role=role,
                content=content,
                token_count=estimate_tokens(content),
                timestamp=ts,
                date=partition_date,
            ))

            # Extract inline tool_calls from assistant messages
            if role == "assistant":
                for tc in msg.get("tool_calls") or []:
                    fn = tc.get("function") or {}
                    all_tool_calls.append(ToolCall(
                        tool_call_id=tc.get("id") or msg_id + "_tc",
                        session_id=session_id,
                        request_id=req_id,
                        turn_index=turn_index,
                        tool_name=fn.get("name", "unknown"),
                        tool_input=fn.get("arguments", "{}"),
                        tool_output=None,  # filled by subsequent tool message
                        timestamp=ts,
                        date=partition_date,
                    ))

        # Back-fill tool_output from role=tool messages
        tool_call_map = {tc.tool_call_id: tc for tc in all_tool_calls if tc.session_id == session_id}
        for msg, introducing_req in deduped:
            if msg.get("role") == "tool":
                tc_id = msg.get("tool_call_id", "")
                if tc_id in tool_call_map:
                    tool_call_map[tc_id].tool_output = _content_str(msg.get("content"))

        all_sessions.append(Session(
            session_id=session_id,
            user_id=user_id,
            team=team,
            agent=agent,
            model=model,
            start_time=start_time,
            end_time=end_time,
            total_requests=len(requests),
            total_messages=len(deduped),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost_usd=round(total_cost, 6),
            date=partition_date,
        ))

    return (
        all_sessions,
        all_messages,
        all_tool_calls,
        all_model_responses,
        list(tool_def_map.values()),
    )
