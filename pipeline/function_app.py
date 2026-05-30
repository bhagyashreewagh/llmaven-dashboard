"""
Azure Functions entry points for the LLMaven ETL pipeline.

Two triggers:
  1. process_new_blob  — fires when a new JSONL file lands in raw/
  2. run_incremental   — timer-based fallback (daily at 01:00 UTC)
"""
import logging
import os
from datetime import date, datetime, timezone

import azure.functions as func

from etl.reader import group_by_session
from etl.storage import (
    get_container_client,
    list_raw_blobs,
    read_jsonl,
    read_watermark,
    write_watermark,
)
from etl.transformer import transform_sessions
from etl.writer import write_all_tables

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

logger = logging.getLogger(__name__)


def _date_from_blob_path(blob_path: str) -> date:
    """Extract date from path like raw/2024-06-01/litellm.jsonl."""
    parts = blob_path.split("/")
    for p in parts:
        try:
            return datetime.strptime(p, "%Y-%m-%d").date()
        except ValueError:
            continue
    return date.today()


def _process_blob(blob_path: str) -> dict:
    container = get_container_client()
    logger.info("Processing blob: %s", blob_path)

    records = read_jsonl(container, blob_path)
    if not records:
        logger.warning("No records in %s", blob_path)
        return {"blob": blob_path, "records": 0}

    sessions = group_by_session(records)
    partition_date = _date_from_blob_path(blob_path)
    date_str = partition_date.isoformat()

    all_sessions, messages, tool_calls, model_responses, tool_defs = transform_sessions(
        sessions, partition_date
    )

    counts = write_all_tables(
        container, date_str,
        all_sessions, messages, tool_calls, model_responses, tool_defs,
    )

    write_watermark(container, blob_path)
    logger.info("Wrote tables for %s: %s", date_str, counts)
    return {"blob": blob_path, "date": date_str, "counts": counts}


@app.blob_trigger(
    arg_name="blob",
    path=f"{os.environ.get('RAW_PREFIX', 'raw')}/{{date}}/{{name}}",
    connection="AzureWebJobsStorage",
)
def process_new_blob(blob: func.InputStream) -> None:
    """Triggered when LiteLLM drops a new JSONL file into the raw zone."""
    _process_blob(blob.name)


@app.event_grid_trigger(arg_name="event")
def process_new_blob_eventgrid(event: func.EventGridEvent) -> None:
    """Event Grid trigger — low-latency alternative to the blob trigger above."""
    import json
    data = event.get_json()
    # Event Grid BlobCreated: data.url = https://<account>.blob.core.windows.net/<container>/raw/...
    blob_url: str = data.get("url", "")
    container_name = os.environ.get("ADLS_CONTAINER", "llmaven")
    # Extract path after /<container>/
    marker = f"/{container_name}/"
    idx = blob_url.find(marker)
    if idx == -1 or not blob_url.endswith(".jsonl"):
        logger.info("Skipping non-JSONL event: %s", blob_url)
        return
    blob_path = blob_url[idx + len(marker):]
    _process_blob(blob_path)


@app.timer_trigger(
    arg_name="timer",
    schedule="0 0 1 * * *",  # daily at 01:00 UTC
    run_on_startup=False,
)
def run_incremental(timer: func.TimerRequest) -> None:
    """
    Fallback: scan for any raw blobs written since the last watermark
    and process them. Ensures nothing is missed if the blob trigger fires
    before LiteLLM finishes writing the file.
    """
    container = get_container_client()
    watermark = read_watermark(container)
    since = watermark.get("last_processed_blob")

    new_blobs = list_raw_blobs(container, since_path=since)
    if not new_blobs:
        logger.info("No new blobs since watermark %s", since)
        return

    for blob_path in new_blobs:
        try:
            result = _process_blob(blob_path)
            logger.info("Timer run processed: %s", result)
        except Exception:
            logger.exception("Failed to process %s — skipping", blob_path)


@app.route(route="status", methods=["GET"])
def pipeline_status(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check that returns the current watermark."""
    container = get_container_client()
    wm = read_watermark(container)
    import json
    return func.HttpResponse(
        json.dumps(wm, default=str),
        mimetype="application/json",
        status_code=200,
    )
