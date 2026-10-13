"""DSPy modules and signatures for DevTrace activity analysis and onboarding synthesis."""

from typing import List
import dspy
import pydantic


import dspy
from typing import List

class DetectContextSwitch(dspy.Signature):
    """
    Analyze chronological developer activity logs.
    Determine if the developer switched their focus to a different project than 'prior_project'.
    A switch occurs if the logs reference a different project_id, branch names from another project,
    tickets prefixed for another project (e.g. BETA-xxx vs ALPHA-xxx), or Pi Agent tasks on a different codebase.
    """
    developer_id: str = dspy.InputField(desc="Unique ID of the developer")
    prior_project: str = dspy.InputField(desc="The project the developer was previously working on")
    recent_events_summary: str = dspy.InputField(desc="Chronological stream of activities with project_id, tools, branch, tickets, and diffs")
    
    switch_detected: bool = dspy.OutputField(desc="True if developer shifted focus to a new project, else False")
    target_project: str = dspy.OutputField(desc="The actual project worked on in these recent events")
    rationale: str = dspy.OutputField(desc="Concise reasoning citing specific tickets, branches, or project_id values observed")
    confidence: float = dspy.OutputField(desc="Confidence score between 0.0 and 1.0")


class SynthesizeOnboardingBrief(dspy.Signature):
    """
    Synthesize trailing activity across repositories and tools into a structured briefing
    for an engineer newly onboarding to the project.
    """
    project_id: str = dspy.InputField(desc="The project being summarized")
    project_event_history: str = dspy.InputField(desc="Trailing chronological logs of commits, tickets, and agent runs")
    
    active_objectives: List[str] = dspy.OutputField(desc="Active tasks, features, or hotfixes underway")
    current_blockers: List[str] = dspy.OutputField(desc="Blocked tickets, failing checks, or urgent P0 items")
    recent_switches: List[str] = dspy.OutputField(desc="Notes on team members who joined, left, or assisted")
    executive_summary: str = dspy.OutputField(desc="2-3 sentence high-level brief for a new engineer")


class DevTraceEngine(dspy.Module):
    def __init__(self):
        super().__init__()
        self.detector = dspy.ChainOfThought(DetectContextSwitch)
        self.summarizer = dspy.ChainOfThought(SynthesizeOnboardingBrief)

    def detect_switch(self, developer_id: str, prior_project: str, recent_events_summary: str):
        return self.detector(
            developer_id=developer_id,
            prior_project=prior_project,
            recent_events_summary=recent_events_summary
        )

    def generate_brief(self, project_id: str, project_event_history: str):
        return self.summarizer(
            project_id=project_id,
            project_event_history=project_event_history
        )