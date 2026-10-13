"""Unit tests for DevTrace modules."""

import unittest
from src.trace_loader import load_traces_from_json
from src.dspy_modules import DevTraceEngine, DetectContextSwitch, SynthesizeOnboardingBrief
from src.ingest_supabase import map_event_record


class TestTraceModules(unittest.TestCase):
    def test_load_traces_nonexistent_file(self):
        traces = load_traces_from_json("nonexistent.json")
        self.assertEqual(traces, [])

    def test_dspy_signatures_and_engine(self):
        engine = DevTraceEngine()
        self.assertIsNotNone(engine.detector)
        self.assertIsNotNone(engine.summarizer)

    def test_map_event_record(self):
        raw_event = {
            "developer": "dev_sanket",
            "project": "Project-Beta",
            "event_type": "jira",
            "action": "ticket_transition",
            "payload": {"ticket_id": "BETA-911", "summary": "Urgent bug fix"},
        }
        mapped = map_event_record(raw_event)
        self.assertEqual(mapped["developer_id"], "dev_sanket")
        self.assertEqual(mapped["project_id"], "Project-Beta")
        self.assertEqual(mapped["source_tool"], "jira")
        self.assertEqual(mapped["event_type"], "ticket_transition")
        self.assertEqual(mapped["content"], "Urgent bug fix")
        self.assertEqual(mapped["metadata"]["ticket_id"], "BETA-911")


if __name__ == "__main__":
    unittest.main()
