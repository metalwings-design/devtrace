"""Simulate 14 days of chronological developer activity logs.

Deterministically generates events for:
- Developers: dev_sanket, dev_alex, dev_elena
- Projects: Project-Alpha, Project-Beta
- Event types: git, jira, pi_agent
Includes an explicit context switch for dev_sanket (Alpha -> Beta on Day 5, back on Day 8).
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import random
import uuid


def generate_simulated_events(seed: int = 42) -> list[dict]:
    random.seed(seed)
    base_date = datetime(2026, 9, 14, 9, 0, 0)
    events: list[dict] = []

    developers = ["dev_sanket", "dev_alex", "dev_elena"]

    # Ticket pool per project
    jira_tickets = {
        "Project-Alpha": ["ALPHA-101", "ALPHA-102", "ALPHA-103", "ALPHA-104"],
        "Project-Beta": ["BETA-201", "BETA-202", "BETA-203", "BETA-204"],
    }

    urgent_ticket = "BETA-911"

    for day in range(1, 15):
        day_start = base_date + timedelta(days=day - 1)

        for dev in developers:
            # Context assignment
            if dev == "dev_sanket":
                if 5 <= day <= 7:
                    project = "Project-Beta"
                else:
                    project = "Project-Alpha"
            elif dev == "dev_alex":
                project = "Project-Alpha"
            else:
                project = "Project-Beta"

            work_hours = random.sample(range(9, 18), 4)
            work_hours.sort()

            # Handle explicit context switch markers for dev_sanket
            if dev == "dev_sanket" and day == 5:
                # Urgent ticket transition to IN_PROGRESS
                t_switch = day_start.replace(hour=9, minute=15, second=0)
                events.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_jira_switch")),
                    "timestamp": t_switch.isoformat(),
                    "developer": dev,
                    "project": "Project-Beta",
                    "event_type": "jira",
                    "action": "ticket_transition",
                    "payload": {
                        "ticket_id": urgent_ticket,
                        "transition": "IN_PROGRESS",
                        "summary": "Urgent production bug: memory leak in auth service",
                        "priority": "P0",
                    },
                })
                # Branch checkout
                events.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_git_checkout")),
                    "timestamp": (t_switch + timedelta(minutes=5)).isoformat(),
                    "developer": dev,
                    "project": "Project-Beta",
                    "event_type": "git",
                    "action": "checkout",
                    "payload": {
                        "branch": "hotfix/BETA-911-auth-leak",
                        "base_branch": "main",
                    },
                })

            if dev == "dev_sanket" and day == 7:
                # Resolve urgent ticket on Project-Beta
                t_resolve = day_start.replace(hour=17, minute=30, second=0)
                events.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_jira_resolve")),
                    "timestamp": t_resolve.isoformat(),
                    "developer": dev,
                    "project": "Project-Beta",
                    "event_type": "jira",
                    "action": "ticket_transition",
                    "payload": {
                        "ticket_id": urgent_ticket,
                        "transition": "DONE",
                        "resolution": "Fixed and verified in staging",
                    },
                })

            if dev == "dev_sanket" and day == 8:
                # Context return back to Project-Alpha
                t_return = day_start.replace(hour=9, minute=10, second=0)
                events.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_return_checkout")),
                    "timestamp": t_return.isoformat(),
                    "developer": dev,
                    "project": "Project-Alpha",
                    "event_type": "git",
                    "action": "checkout",
                    "payload": {
                        "branch": "feature/ALPHA-101-core-pipeline",
                        "base_branch": "main",
                    },
                })

            # Daily regular events for each dev
            curr_ticket = random.choice(jira_tickets[project])

            # 1. Jira transition
            jira_time = day_start.replace(hour=work_hours[0], minute=random.randint(5, 25))
            transition = random.choice(["IN_PROGRESS", "BLOCKED", "DONE"])
            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_jira")),
                "timestamp": jira_time.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "jira",
                "action": "ticket_transition",
                "payload": {
                    "ticket_id": curr_ticket,
                    "transition": transition,
                    "comment": f"Updated ticket status to {transition}",
                },
            })

            # 2. Git events (commits / pr reviews)
            git_time = day_start.replace(hour=work_hours[1], minute=random.randint(10, 45))
            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_commit")),
                "timestamp": git_time.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "git",
                "action": "commit",
                "payload": {
                    "commit_hash": uuid.uuid4().hex[:8],
                    "branch": f"{dev}/feature-work",
                    "message": f"feat({curr_ticket}): routine updates and tests",
                },
            })

            # Optional PR Review
            pr_time = day_start.replace(hour=work_hours[2], minute=random.randint(15, 50))
            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_pr_review")),
                "timestamp": pr_time.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "git",
                "action": "pr_review",
                "payload": {
                    "pr_id": random.randint(10, 99),
                    "review_status": "APPROVED",
                },
            })

            # 3. pi_agent session (pi_session_start -> pi_tool_call -> pi_session_end)
            session_id = f"pi_sess_{dev}_{day}"
            pi_start = day_start.replace(hour=work_hours[3], minute=5)
            pi_tool = pi_start + timedelta(minutes=random.randint(3, 8))
            pi_end = pi_tool + timedelta(minutes=random.randint(5, 12))

            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_pi_start")),
                "timestamp": pi_start.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "pi_agent",
                "action": "pi_session_start",
                "payload": {
                    "session_id": session_id,
                    "agent_mode": "developer_assistant",
                },
            })

            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_pi_tool")),
                "timestamp": pi_tool.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "pi_agent",
                "action": "pi_tool_call",
                "payload": {
                    "session_id": session_id,
                    "tool": random.choice(["search_code", "run_linter", "run_unit_tests"]),
                    "arguments": {"ticket": curr_ticket},
                },
            })

            events.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dev}_{day}_pi_end")),
                "timestamp": pi_end.isoformat(),
                "developer": dev,
                "project": project,
                "event_type": "pi_agent",
                "action": "pi_session_end",
                "payload": {
                    "session_id": session_id,
                    "status": "completed",
                },
            })

    # Sort strictly chronologically
    events.sort(key=lambda e: e["timestamp"])
    return events


def main():
    events = generate_simulated_events(seed=42)
    output_dir = Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "simulated_events.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    print(f"Generated {len(events)} events saved to {output_file}")


if __name__ == "__main__":
    main()
