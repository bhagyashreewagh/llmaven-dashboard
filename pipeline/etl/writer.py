"""
Serialize dataclass lists to Parquet and upload to ADLS Gen2.
Each table is written as a single Parquet file partitioned by date.
"""
import dataclasses
from datetime import date
from io import BytesIO

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .models import Message, ModelResponse, Session, ToolCall, ToolDefinition
from .storage import ContainerClient, write_parquet


def _to_df(items: list) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()
    return pd.DataFrame([dataclasses.asdict(i) for i in items])


def _df_to_parquet_bytes(df: pd.DataFrame) -> BytesIO:
    buf = BytesIO()
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, buf, compression="snappy")
    return buf


def write_all_tables(
    container: ContainerClient,
    date_str: str,
    sessions: list[Session],
    messages: list[Message],
    tool_calls: list[ToolCall],
    model_responses: list[ModelResponse],
    tool_definitions: list[ToolDefinition],
) -> dict[str, int]:
    """Write all five tables to ADLS Gen2. Returns row counts per table."""
    counts = {}

    tables = [
        ("sessions", sessions),
        ("messages", messages),
        ("tool_calls", tool_calls),
        ("model_responses", model_responses),
    ]
    for name, rows in tables:
        df = _to_df(rows)
        if not df.empty:
            write_parquet(container, name, date_str, _df_to_parquet_bytes(df))
        counts[name] = len(rows)

    # tool_definitions are global (no date partition)
    if tool_definitions:
        df = _to_df(tool_definitions)
        buf = _df_to_parquet_bytes(df)
        buf.seek(0)
        container.get_blob_client("processed/tool_definitions/part.parquet").upload_blob(
            buf, overwrite=True
        )
    counts["tool_definitions"] = len(tool_definitions)

    return counts
