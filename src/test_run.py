import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")


def main():
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not found in .env")

    raw_model = os.getenv("DSPY_MODEL", "openai/gpt-oss-120b")
    # On Groq, the model ID is literally "openai/gpt-oss-120b".
    # DSPy treats the prefix before the first slash as provider, so we pass openai/<model_id>.
    dspy_model_spec = f"openai/{raw_model}" if not raw_model.startswith("openai/openai/") else raw_model

    import dspy
    from src.dspy_modules import DevTraceEngine

    lm = dspy.LM(
        model=dspy_model_spec,
        api_key=groq_key,
        api_base="https://api.groq.com/openai/v1",
    )
    dspy.configure(lm=lm)

    data_path = ROOT_DIR / "data" / "simulated_events.json"
    with open(data_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    sanket_beta_events = []
    for e in events:
        raw_str = json.dumps(e).lower()
        if "sanket" in raw_str and ("beta" in raw_str or "911" in raw_str):
            sanket_beta_events.append(e)

    print(f"Total events in dataset: {len(events)}")
    print(f"Matched {len(sanket_beta_events)} switch events for dev_sanket on Project-Beta.")

    event_lines = []
    for e in sanket_beta_events[:15]:
        timestamp = e.get("timestamp", "")
        project = e.get("project_id") or e.get("project", "Unknown")
        source = e.get("source_tool") or (e.get("event_type") if e.get("event_type") in ["git", "jira", "pi_agent"] else "git")
        event_type = e.get("action") or e.get("event_type", "activity")
        payload = e.get("payload") or e.get("metadata") or {}
        content = e.get("content") or payload.get("summary") or payload.get("message") or payload.get("comment") or payload.get("tool") or f"{event_type}"
        event_lines.append(
            f"[{timestamp}] Project: {project} | Tool: {source} | Event: {event_type} | Content: {content} | Meta: {payload}"
        )

    event_summary = "\n".join(event_lines)

    print("\n--- Formatted Input Sent to Model (first 3 lines) ---")
    for line in event_lines[:3]:
        print(line)

    print("\n--- Running Context Switch Detection via Groq ---")
    engine = DevTraceEngine()
    result = engine.detect_switch(
        developer_id="dev_sanket",
        prior_project="Project-Alpha",
        recent_events_summary=event_summary,
    )

    print(f"\nSwitch Detected : {result.switch_detected}")
    print(f"Target Project  : {result.target_project}")
    print(f"Confidence      : {result.confidence}")
    print(f"Rationale       : {result.rationale}")


if __name__ == "__main__":
    main()