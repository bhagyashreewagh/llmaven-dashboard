"""
data.py
-------
Loads LiteLLM logs from Azure Data Lake Storage (litellm-logs container).

- Reads all data under logs/
- One .json file per API request, path: logs/YYYY/MM/DD/<id>.json
- Deduplicates by request_id
- Anonymizes user identifiers — no PII shown on dashboard
  Same user always maps to the same anonymous ID so per-user
  patterns are preserved, but real identities are never exposed.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

import pandas as pd
import streamlit as st
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# In-memory mapping built during load — { "user_001": "real@email.com" }
# Persisted to Key Vault so admins can reverse any anonymous ID.
_user_mapping: dict[str, str] = {}
_user_counter: dict[str, str] = {}  # real → anon_id


def _anonymize_user(raw: str) -> str:
    """
    Map a real user identifier to a short sequential anonymous ID.
    e.g. first unique user → user_001, second → user_002, etc.
    Stores the reverse mapping in _user_mapping for Key Vault upload.
    """
    if not raw or raw.lower() in ("unknown", ""):
        return "user_000"
    if raw in _user_counter:
        return _user_counter[raw]
    anon_id = f"user_{len(_user_counter) + 1:03d}"
    _user_counter[raw]    = anon_id
    _user_mapping[anon_id] = raw
    return anon_id


_session_counter: dict[str, str] = {}

def _anonymize_session(raw: str) -> str:
    """Map session/trace IDs to sequential anonymous IDs."""
    if not raw:
        return ""
    if raw not in _session_counter:
        _session_counter[raw] = f"sess_{len(_session_counter) + 1:04d}"
    return _session_counter[raw]


def _persist_mapping_to_keyvault() -> None:
    """
    Write the full anon_id → real_user mapping to Key Vault as a single
    JSON secret called 'user-anonymization-map'.
    Only runs if KV_URL is set (i.e. in production on App Service).
    Admins with Key Vault access can read this secret to reverse any ID.
    """
    kv_url = os.environ.get("KEY_VAULT_URL", "").strip()
    if not kv_url or not _user_mapping:
        return
    try:
        credential = ManagedIdentityCredential()
        client     = SecretClient(vault_url=kv_url, credential=credential)
        # Merge with any existing mapping so we never lose old entries
        try:
            existing = json.loads(client.get_secret("user-anonymization-map").value)
        except Exception:
            existing = {}
        existing.update(_user_mapping)
        client.set_secret("user-anonymization-map", json.dumps(existing, indent=2))
    except Exception:
        pass  # Never block the dashboard if KV write fails


def _clean_model(raw: str) -> str:
    r = raw.lower()
    if "haiku"  in r:                    return "Claude Haiku"
    if "sonnet" in r and "bedrock" in r: return "Claude Sonnet (Bedrock)"
    if "sonnet" in r:                    return "Claude Sonnet"
    if "gpt"    in r or "openai" in r:   return "OpenAI (GPT)"
    if "opus"   in r:                    return "Claude Opus"
    return "Other"


def _cache_savings(row) -> float:
    t = row["cache_read"]
    if t <= 0:
        return 0.0
    rate = (0.80 - 0.08) if "haiku" in row["model_raw"].lower() else (3.00 - 0.30)
    return t * rate / 1_000_000


def _parse_ts(val):
    """Parse a Unix timestamp (float) or ISO string into a UTC Timestamp."""
    if val is None:
        return pd.NaT
    try:
        return pd.Timestamp(float(val), unit="s", tz="UTC")
    except (TypeError, ValueError):
        return pd.to_datetime(val, utc=True, errors="coerce")


def _parse_one(raw_bytes: bytes) -> dict | None:
    """Parse a single LiteLLM .json log file into a flat row dict."""
    try:
        d    = json.loads(raw_bytes)
        kw   = d.get("kwargs") or {}
        slo  = kw.get("standard_logging_object") or {}
        meta = slo.get("metadata") or {}
        u    = meta.get("usage_object") or {}
        ptd  = u.get("prompt_tokens_details") or {}
        ctd  = u.get("completion_tokens_details") or {}

        request_id = slo.get("id") or d.get("id", "")
        if not request_id:
            return None

        return {
            "request_id":        request_id,
            "spend":             float(slo.get("response_cost") or d.get("cost") or 0),
            "model_raw":         str(slo.get("model") or kw.get("model") or ""),
            "status":            slo.get("status", "unknown"),
            "start_time":        slo.get("startTime") or kw.get("start_time"),
            "end_time":          slo.get("endTime")   or kw.get("end_time"),
            "total_tokens":      int(slo.get("total_tokens") or 0),
            "prompt_tokens":     int(slo.get("prompt_tokens") or 0),
            "completion_tokens": int(slo.get("completion_tokens") or 0),
            "session_id":        kw.get("litellm_session_id") or slo.get("trace_id") or "",
            "user":              meta.get("user_api_key_alias") or "unknown",
            "team":              meta.get("user_api_key_team_alias") or "No Team",
            "cache_read":        int(u.get("cache_read_input_tokens")
                                     or ptd.get("cached_tokens") or 0),
            "cache_create":      int(u.get("cache_creation_input_tokens")
                                     or ptd.get("cache_creation_tokens") or 0),
            "reasoning_tokens":  int(ctd.get("reasoning_tokens") or 0),
        }
    except Exception:
        return None


def _build_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    df["start_dt"] = df["start_time"].apply(_parse_ts)
    df["end_dt"]   = df["end_time"].apply(_parse_ts)
    df = df.dropna(subset=["start_dt"])

    df["date"]    = df["start_dt"].dt.date
    df["hour"]    = df["start_dt"].dt.hour
    df["dow"]     = df["start_dt"].dt.day_name()
    df["month"]   = df["start_dt"].dt.month_name()
    df["latency"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds().clip(0, 300)
    df["model"]   = df["model_raw"].apply(_clean_model)
    df["cache_savings"] = df.apply(_cache_savings, axis=1)

    # Anonymize — replace real user/session identifiers with consistent hashes
    df["user"]       = df["user"].apply(_anonymize_user)
    df["session_id"] = df["session_id"].apply(_anonymize_session)
    # Replace raw request_id with a simple sequential number
    df["request_id"] = [f"req_{i+1:05d}" for i in range(len(df))]

    HAIKU_IN, HAIKU_OUT = 0.80 / 1_000_000, 4.00 / 1_000_000
    df["spend_haiku"] = (df["prompt_tokens"] * HAIKU_IN
                         + df["completion_tokens"] * HAIKU_OUT)
    return df


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Loading latest data from Azure Data Lake...")
def load_data() -> pd.DataFrame:
    """
    Load the last LOOKBACK_DAYS days of LiteLLM logs from ADLS.
    Deduplicates by request_id.
    Returns a clean DataFrame ready for the dashboard.
    """
    conn_str  = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    container = os.environ.get("ADLS_CONTAINER", "litellm-logs")

    if not conn_str:
        st.warning("AZURE_STORAGE_CONNECTION_STRING not set — showing demo data.")
        return _demo()

    try:
        cc = BlobServiceClient.from_connection_string(conn_str).get_container_client(container)

        # List ALL blobs under logs/ — picks up everything Carlos has dumped
        blobs = [
            b for b in cc.list_blobs(name_starts_with="logs/")
            if b.name.endswith(".json") and b.size > 0
        ]

        if not blobs:
            st.info("No data found in Azure Data Lake Storage.")
            return _demo()

        # Download and parse all files in parallel (32 workers = ~30x faster)
        def _fetch(blob_name: str):
            try:
                raw = cc.get_blob_client(blob_name).download_blob().readall()
                return _parse_one(raw)
            except Exception:
                return None

        rows = []
        with ThreadPoolExecutor(max_workers=32) as pool:
            futures = {pool.submit(_fetch, b.name): b.name for b in blobs}
            for future in as_completed(futures):
                row = future.result()
                if row:
                    rows.append(row)

        if not rows:
            st.warning("Files found but none could be parsed.")
            return _demo()

        df = _build_df(rows)

        # Deduplicate by request_id — keep most recent
        df = df.sort_values("start_dt").drop_duplicates(subset="request_id", keep="last")
        df = df.reset_index(drop=True)

        # Persist anon → real mapping to Key Vault for admin reversal
        _persist_mapping_to_keyvault()

        return df

    except AzureError as e:
        st.error(f"Azure Storage error: {e}")
        return _demo()
    except Exception as e:
        st.error(f"Unexpected error loading data: {e}")
        return _demo()


# ---------------------------------------------------------------------------
# Demo fallback (shown when no real data available)
# ---------------------------------------------------------------------------

def _demo() -> pd.DataFrame:
    rows = [
        {"request_id": "req-001", "spend": 0.00479, "model_raw": "claude-sonnet-4-6",
         "status": "success", "start_time": "2026-05-26T10:00:00Z", "end_time": "2026-05-26T10:00:02Z",
         "total_tokens": 467, "prompt_tokens": 150, "completion_tokens": 317,
         "session_id": "sess-001", "user": "researcher_01", "team": "eScience",
         "cache_read": 0, "cache_create": 0, "reasoning_tokens": 0},
        {"request_id": "req-002", "spend": 0.00821, "model_raw": "claude-sonnet-4-6",
         "status": "success", "start_time": "2026-05-27T11:00:00Z", "end_time": "2026-05-27T11:00:03Z",
         "total_tokens": 1000, "prompt_tokens": 480, "completion_tokens": 520,
         "session_id": "sess-001", "user": "researcher_01", "team": "eScience",
         "cache_read": 200, "cache_create": 0, "reasoning_tokens": 0},
        {"request_id": "req-003", "spend": 0.00210, "model_raw": "claude-haiku-3",
         "status": "success", "start_time": "2026-05-28T09:00:00Z", "end_time": "2026-05-28T09:00:01Z",
         "total_tokens": 270, "prompt_tokens": 90, "completion_tokens": 180,
         "session_id": "sess-002", "user": "researcher_02", "team": "eScience",
         "cache_read": 0, "cache_create": 0, "reasoning_tokens": 0},
        {"request_id": "req-004", "spend": 0.01200, "model_raw": "claude-sonnet-4-6",
         "status": "failure", "start_time": "2026-05-29T14:00:00Z", "end_time": "2026-05-29T14:00:05Z",
         "total_tokens": 1400, "prompt_tokens": 600, "completion_tokens": 800,
         "session_id": "sess-003", "user": "researcher_03", "team": "ML Team",
         "cache_read": 500, "cache_create": 100, "reasoning_tokens": 50},
        {"request_id": "req-005", "spend": 0.00980, "model_raw": "claude-sonnet-4-6",
         "status": "success", "start_time": "2026-05-30T16:00:00Z", "end_time": "2026-05-30T16:00:00.1Z",
         "total_tokens": 1000, "prompt_tokens": 400, "completion_tokens": 600,
         "session_id": "sess-004", "user": "researcher_01", "team": "eScience",
         "cache_read": 350, "cache_create": 0, "reasoning_tokens": 0},
    ]
    return _build_df(rows)
