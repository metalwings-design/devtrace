"""Self-contained evaluation and optimization harness for DevTrace context switch detector."""

import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(ROOT_DIR / ".env")

import dspy
from src.dspy_modules import DetectContextSwitch


def init_lm():
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


def build_dataset() -> list[dspy.Example]:
    """Build 14 labeled examples of switch and non-switch scenarios."""
    raw_data = [
        # 1. Switch to Beta on urgent bug
        {
            "developer_id": "dev_sanket",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-18T09:15:00] Project: Project-Beta | Event: ticket_transition | Content: Urgent P0 bug BETA-911 auth crash\n[2026-09-18T09:20:00] Project: Project-Beta | Event: checkout hotfix/BETA-911",
            "switch_detected": True,
            "target_project": "Project-Beta",
        },
        # 2. Non-switch on Alpha routine commit
        {
            "developer_id": "dev_alex",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-18T10:00:00] Project: Project-Alpha | Event: commit feat(ALPHA-101): implement caching layer\n[2026-09-18T11:00:00] Project: Project-Alpha | Event: pr_review approved PR #22",
            "switch_detected": False,
            "target_project": "Project-Alpha",
        },
        # 3. Switch to Alpha from Beta
        {
            "developer_id": "dev_elena",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-19T09:30:00] Project: Project-Alpha | Event: checkout feature/ALPHA-205-search\n[2026-09-19T10:15:00] Project: Project-Alpha | Event: ticket_transition ALPHA-205 to IN_PROGRESS",
            "switch_detected": True,
            "target_project": "Project-Alpha",
        },
        # 4. Non-switch on Beta routine task
        {
            "developer_id": "dev_elena",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-19T14:00:00] Project: Project-Beta | Event: commit fix(BETA-302): fix date parser\n[2026-09-19T15:30:00] Project: Project-Beta | Event: pi_tool_call run_unit_tests",
            "switch_detected": False,
            "target_project": "Project-Beta",
        },
        # 5. Switch to Beta hotfix checkout
        {
            "developer_id": "dev_alex",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-20T11:00:00] Project: Project-Beta | Event: checkout hotfix/BETA-404-api-timeout\n[2026-09-20T11:20:00] Project: Project-Beta | Event: ticket_transition BETA-404 IN_PROGRESS",
            "switch_detected": True,
            "target_project": "Project-Beta",
        },
        # 6. Non-switch Alpha continuous commits
        {
            "developer_id": "dev_sanket",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-21T09:00:00] Project: Project-Alpha | Event: commit refactor(ALPHA-103): database pooling\n[2026-09-21T10:00:00] Project: Project-Alpha | Event: ticket_transition ALPHA-103 DONE",
            "switch_detected": False,
            "target_project": "Project-Alpha",
        },
        # 7. Switch back from Beta to Alpha
        {
            "developer_id": "dev_sanket",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-21T14:00:00] Project: Project-Alpha | Event: checkout main\n[2026-09-21T14:15:00] Project: Project-Alpha | Event: ticket_transition ALPHA-104 IN_PROGRESS",
            "switch_detected": True,
            "target_project": "Project-Alpha",
        },
        # 8. Non-switch Beta ticket resolution
        {
            "developer_id": "dev_elena",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-22T10:00:00] Project: Project-Beta | Event: commit test(BETA-201): add e2e test suite\n[2026-09-22T11:00:00] Project: Project-Beta | Event: ticket_transition BETA-201 DONE",
            "switch_detected": False,
            "target_project": "Project-Beta",
        },
        # 9. Switch to Beta incident response
        {
            "developer_id": "dev_alex",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-22T13:00:00] Project: Project-Beta | Event: ticket_transition BETA-808 BLOCKED by infra\n[2026-09-22T13:20:00] Project: Project-Beta | Event: checkout fix/BETA-808",
            "switch_detected": True,
            "target_project": "Project-Beta",
        },
        # 10. Non-switch Alpha agent session
        {
            "developer_id": "dev_alex",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-23T09:00:00] Project: Project-Alpha | Event: pi_session_start debugging\n[2026-09-23T09:10:00] Project: Project-Alpha | Event: pi_tool_call search_code for ALPHA-105",
            "switch_detected": False,
            "target_project": "Project-Alpha",
        },
        # 11. Switch to Alpha feature build
        {
            "developer_id": "dev_elena",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-23T14:00:00] Project: Project-Alpha | Event: ticket_transition ALPHA-301 IN_PROGRESS\n[2026-09-23T14:10:00] Project: Project-Alpha | Event: checkout feature/ALPHA-301",
            "switch_detected": True,
            "target_project": "Project-Alpha",
        },
        # 12. Non-switch Beta code review
        {
            "developer_id": "dev_elena",
            "prior_project": "Project-Beta",
            "recent_events_summary": "[2026-09-24T09:00:00] Project: Project-Beta | Event: pr_review PR #44 approved\n[2026-09-24T10:00:00] Project: Project-Beta | Event: commit docs(BETA): update API documentation",
            "switch_detected": False,
            "target_project": "Project-Beta",
        },
        # 13. Switch to Beta deployment
        {
            "developer_id": "dev_sanket",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-24T13:00:00] Project: Project-Beta | Event: checkout release/BETA-v1.2\n[2026-09-24T13:30:00] Project: Project-Beta | Event: ticket_transition BETA-500 IN_PROGRESS",
            "switch_detected": True,
            "target_project": "Project-Beta",
        },
        # 14. Non-switch Alpha unit tests
        {
            "developer_id": "dev_sanket",
            "prior_project": "Project-Alpha",
            "recent_events_summary": "[2026-09-25T10:00:00] Project: Project-Alpha | Event: pi_tool_call run_unit_tests ALPHA-101\n[2026-09-25T11:00:00] Project: Project-Alpha | Event: commit fix(ALPHA-101): resolve edge case",
            "switch_detected": False,
            "target_project": "Project-Alpha",
        },
    ]

    examples = []
    for item in raw_data:
        ex = dspy.Example(
            developer_id=item["developer_id"],
            prior_project=item["prior_project"],
            recent_events_summary=item["recent_events_summary"],
            switch_detected=item["switch_detected"],
            target_project=item["target_project"],
        ).with_inputs("developer_id", "prior_project", "recent_events_summary")
        examples.append(ex)

    return examples


def strict_switch_metric(example, pred, trace=None) -> bool:
    """Strict evaluation metric:

    1. Checks if switch_detected matches example.switch_detected.
    2. If switch_detected is True, also verifies target_project matches.
    """
    pred_switch = bool(getattr(pred, "switch_detected", False))
    ex_switch = bool(example.switch_detected)

    if pred_switch != ex_switch:
        return False

    if ex_switch:
        ex_target = (example.target_project or "").strip().lower()
        pred_target = (getattr(pred, "target_project", "") or "").strip().lower()
        return ex_target == pred_target

    return True


def evaluate_dataset(module, dataset) -> float:
    """Evaluate module on dataset and return percentage accuracy."""
    correct = 0
    for ex in dataset:
        pred = module(
            developer_id=ex.developer_id,
            prior_project=ex.prior_project,
            recent_events_summary=ex.recent_events_summary,
        )
        if strict_switch_metric(ex, pred):
            correct += 1
    return (correct / len(dataset)) * 100.0 if dataset else 0.0


def main():
    init_lm()
    dataset = build_dataset()

    # Split: 8 train examples, 6 test examples
    trainset = dataset[:8]
    testset = dataset[8:]
    print(f"Dataset loaded: {len(trainset)} train examples, {len(testset)} test examples.")

    # 1. Zero-shot baseline evaluation
    print("\nEvaluating baseline zero-shot detector...")
    baseline_detector = dspy.ChainOfThought(DetectContextSwitch)
    baseline_acc = evaluate_dataset(baseline_detector, testset)
    print(f"Baseline Zero-Shot Accuracy: {baseline_acc:.1f}%")

    # 2. Compile using BootstrapFewShot
    print("\nCompiling detector with BootstrapFewShot (max_bootstrapped_demos=3)...")
    teleprompter = dspy.teleprompt.BootstrapFewShot(
        metric=strict_switch_metric,
        max_bootstrapped_demos=3,
        max_labeled_demos=3,
    )
    compiled_detector = teleprompter.compile(
        student=baseline_detector,
        trainset=trainset,
    )

    # 3. Evaluate compiled module
    print("Evaluating compiled detector on test set...")
    compiled_acc = evaluate_dataset(compiled_detector, testset)
    print(f"Compiled Detector Accuracy:  {compiled_acc:.1f}%")

    # 4. Save compiled artifact
    output_path = ROOT_DIR / "compiled_devtrace.json"
    compiled_detector.save(str(output_path))
    print(f"Saved compiled artifact to: {output_path.name}")

    # 5. Formatted Comparison Summary
    print("\n" + "=" * 50)
    print("Optimization Results Summary:")
    print(f"  - Baseline Accuracy : {baseline_acc:.1f}%")
    print(f"  - Compiled Accuracy : {compiled_acc:.1f}%")
    print(f"  - Artifact Location : {output_path.name}")
    print("=" * 50)


if __name__ == "__main__":
    main()
