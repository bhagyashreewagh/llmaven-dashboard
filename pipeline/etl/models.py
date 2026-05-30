"""
Dataclasses for the five output tables.
All timestamps are UTC, all costs in USD.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class Session:
    session_id: str
    user_id: str
    team: str
    agent: str
    model: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    date: date


@dataclass
class Message:
    message_id: str
    session_id: str
    request_id: str
    turn_index: int
    role: str
    content: str
    token_count: int
    timestamp: datetime
    date: date


@dataclass
class ToolCall:
    tool_call_id: str
    session_id: str
    request_id: str
    turn_index: int
    tool_name: str
    tool_input: str
    tool_output: Optional[str]
    timestamp: datetime
    date: date


@dataclass
class ModelResponse:
    request_id: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float
    latency_ms: int
    stop_reason: str
    timestamp: datetime
    date: date


@dataclass
class ToolDefinition:
    tool_hash: str
    name: str
    description: str
    input_schema: str
    first_seen: datetime
