"""
Azure Data Lake Storage Gen2 helpers.
All paths are blob paths relative to the container root.
"""
import json
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from azure.storage.blob import BlobServiceClient, ContainerClient


def get_container_client() -> ContainerClient:
    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ.get("ADLS_CONTAINER", "llmaven")
    return BlobServiceClient.from_connection_string(conn).get_container_client(container)


def list_raw_blobs(container: ContainerClient, since_path: str | None = None) -> list[str]:
    """Return sorted list of raw JSONL blob paths, optionally filtered to those after since_path."""
    prefix = os.environ.get("RAW_PREFIX", "raw")
    blobs = sorted(b.name for b in container.list_blobs(name_starts_with=prefix + "/"))
    if since_path:
        blobs = [b for b in blobs if b > since_path]
    return blobs


def read_jsonl(container: ContainerClient, blob_path: str) -> list[dict]:
    """Download a JSONL blob and parse each line into a dict."""
    data = container.get_blob_client(blob_path).download_blob().readall()
    records = []
    for line in data.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def read_watermark(container: ContainerClient) -> dict[str, Any]:
    checkpoint_path = os.environ.get("CHECKPOINT_PATH", "checkpoints/watermark.json")
    try:
        data = container.get_blob_client(checkpoint_path).download_blob().readall()
        return json.loads(data)
    except Exception:
        return {"last_processed_blob": None, "processed_at": None}


def write_watermark(container: ContainerClient, last_blob: str) -> None:
    checkpoint_path = os.environ.get("CHECKPOINT_PATH", "checkpoints/watermark.json")
    payload = json.dumps({
        "last_processed_blob": last_blob,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")
    container.get_blob_client(checkpoint_path).upload_blob(payload, overwrite=True)


def write_parquet(container: ContainerClient, table_name: str, date_str: str, buf: BytesIO) -> None:
    prefix = os.environ.get("PROCESSED_PREFIX", "processed")
    path = f"{prefix}/{table_name}/date={date_str}/part.parquet"
    buf.seek(0)
    container.get_blob_client(path).upload_blob(buf, overwrite=True)
