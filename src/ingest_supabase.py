"""Ingest simulated developer events into Supabase developer_events table."""

import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from supabase import Client, create_client

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing from .env")
    return create_client(supabase_url, supabase_key)


def extract_content(payload: dict, action: str) -> str:
    if not payload:
        return action or "Developer activity"
    return (
        payload.get("summary")
        or payload.get("message")
        or payload.get("comment")
        or payload.get("tool")
        or payload.get("transition")
        or f"{action}: {payload}"
    )


def map_event_record(e: dict) -> dict:
    raw_event_type = e.get("event_type", "")
    action = e.get("action", "")
    payload = e.get("payload") or e.get("metadata") or {}

    # Determine tool and action
    if raw_event_type in ["git", "jira", "pi_agent", "slack"]:
        source_tool = raw_event_type
        event_type = action or raw_event_type
    else:
        source_tool = e.get("source_tool") or e.get("source") or "git"
        event_type = action or raw_event_type or "activity"

    developer_id = e.get("developer_id") or e.get("developer") or e.get("dev_id", "dev_unknown")
    project_id = e.get("project_id") or e.get("project", "Project-Alpha")
    content = e.get("content") or extract_content(payload, event_type)

    return {
        "timestamp": e.get("timestamp"),
        "developer_id": developer_id,
        "source_tool": source_tool,
        "project_id": project_id,
        "event_type": event_type,
        "content": content,
        "metadata": payload,
    }


def ingest_events(batch_size: int = 50, clear_first: bool = False):
    supabase = get_supabase_client()
    data_path = ROOT_DIR / "data" / "simulated_events.json"

    with open(data_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events from {data_path.name}")
    formatted_records = [map_event_record(e) for e in events]

    if clear_first:
        print("Clearing existing developer_events records...")
        supabase.table("developer_events").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print(f"Uploading to Supabase table 'developer_events' in batches of {batch_size}...")
    total_inserted = 0
    for i in range(0, len(formatted_records), batch_size):
        batch = formatted_records[i : i + batch_size]
        supabase.table("developer_events").insert(batch).execute()
        total_inserted += len(batch)
        print(f"  Inserted {total_inserted}/{len(formatted_records)} records")

    print("\nIngestion complete.")
    return total_inserted


if __name__ == "__main__":
    # Clear old malformed rows and re-ingest clean records
    ingest_events(batch_size=50, clear_first=True)