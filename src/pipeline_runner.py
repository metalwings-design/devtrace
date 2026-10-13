"""DevTrace automated end-to-end pipeline runner.

1. Ingests and orders developer activity from Supabase 'developer_events'.
2. Detects project context switches using DevTraceEngine and records them to 'context_switches'.
3. Generates project onboarding briefs and stores them in 'project_onboarding_briefs'.
"""

import json
import os
from pathlib import Path
import sys

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import dspy
from supabase import Client, create_client
from src.dspy_modules import DevTraceEngine

load_dotenv(ROOT_DIR / ".env")


def init_clients() -> Client:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY missing from .env")

    raw_model = os.getenv("DSPY_MODEL", "openai/gpt-oss-120b")
    dspy_model_spec = f"openai/{raw_model}" if not raw_model.startswith("openai/openai/") else raw_model

    lm = dspy.LM(
        model=dspy_model_spec,
        api_key=groq_key,
        api_base="https://api.groq.com/openai/v1",
    )
    dspy.configure(lm=lm)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing from .env")

    return create_client(supabase_url, supabase_key)


def format_event_line(e: dict) -> str:
    ts = e.get("timestamp", "")
    dev = e.get("developer_id", "")
    proj = e.get("project_id", "")
    tool = e.get("source_tool", "")
    etype = e.get("event_type", "")
    content = e.get("content", "")
    meta = e.get("metadata", {})
    return f"[{ts}] Dev: {dev} | Project: {proj} | Tool: {tool} | Event: {etype} | Content: {content} | Meta: {meta}"


def run_pipeline():
    supabase = init_clients()
    engine = DevTraceEngine()

    # 1. Fetch developer events
    print("Fetching developer_events from Supabase...")
    res = supabase.table("developer_events").select("*").order("timestamp", desc=False).execute()
    events = res.data or []
    print(f"Scanned {len(events)} events.")

    # 2. Group by developer_id
    dev_events_map: dict[str, list[dict]] = {}
    for e in events:
        dev_id = e.get("developer_id", "unknown")
        dev_events_map.setdefault(dev_id, []).append(e)

    # 3. Detect Context Switches per developer
    switches_detected = 0
    for dev_id, dev_timeline in dev_events_map.items():
        if not dev_timeline:
            continue

        current_project = dev_timeline[0].get("project_id", "Project-Alpha")
        window_buffer: list[dict] = []

        for event in dev_timeline:
            window_buffer.append(event)
            event_proj = event.get("project_id")

            # Check for candidate switch
            if event_proj and event_proj != current_project:
                context_window = window_buffer[-10:]
                summary_text = "\n".join(format_event_line(x) for x in context_window)

                print(f"\nEvaluating potential switch for {dev_id}: {current_project} -> {event_proj}")
                pred = engine.detect_switch(
                    developer_id=dev_id,
                    prior_project=current_project,
                    recent_events_summary=summary_text,
                )

                if pred.switch_detected:
                    target_project = pred.target_project or event_proj
                    conf = float(getattr(pred, "confidence", 1.0) or 1.0)
                    reason = pred.rationale or f"Detected shift to {target_project}"

                    switch_record = {
                        "developer_id": dev_id,
                        "switched_at": event.get("timestamp"),
                        "from_project": current_project,
                        "to_project": target_project,
                        "reason": reason,
                        "confidence_score": conf,
                    }
                    supabase.table("context_switches").insert(switch_record).execute()
                    switches_detected += 1
                    print(f"  [+] Logged switch for {dev_id}: {current_project} -> {target_project} (Conf: {conf:.2f})")

                    current_project = target_project
                    window_buffer = [event]

    # 4. Generate Project Onboarding Briefs
    target_projects = ["Project-Alpha", "Project-Beta"]
    briefs_generated = 0

    for project_id in target_projects:
        proj_events = [e for e in events if e.get("project_id") == project_id]
        if not proj_events:
            continue

        print(f"\nGenerating onboarding brief for {project_id} ({len(proj_events)} events)...")
        event_history_str = "\n".join(format_event_line(e) for e in proj_events[-40:])

        brief_pred = engine.generate_brief(
            project_id=project_id,
            project_event_history=event_history_str,
        )

        active_objs = getattr(brief_pred, "active_objectives", []) or []
        blockers = getattr(brief_pred, "current_blockers", []) or []
        switches = getattr(brief_pred, "recent_switches", []) or []
        raw_summary = getattr(brief_pred, "executive_summary", "") or ""

        brief_record = {
            "project_id": project_id,
            "active_objectives": active_objs,
            "current_blockers": blockers,
            "recent_switches": switches,
            "raw_summary": raw_summary,
        }
        supabase.table("project_onboarding_briefs").insert(brief_record).execute()
        briefs_generated += 1
        print(f"  [+] Saved onboarding brief for {project_id}.")

    # Summary
    print("\n" + "=" * 50)
    print("Pipeline Execution Summary:")
    print(f"  - Total events scanned:    {len(events)}")
    print(f"  - Context switches logged: {switches_detected}")
    print(f"  - Onboarding briefs saved: {briefs_generated}")
    print("=" * 50)


if __name__ == "__main__":
    run_pipeline()
