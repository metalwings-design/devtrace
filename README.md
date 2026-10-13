# DevTrace: Automated Developer Context-Switch Detection & Onboarding Synthesis Engine

An AI-native engineering telemetry pipeline that continuously monitors developer activity streams across Git, Jira, and autonomous coding agents, autonomously flags project context switches, and synthesizes structured onboarding briefs.

---

## 1. Project Overview & Problem Statement

### Context
Modern software engineering happens across fragmented tools: Git repositories, Jira issue trackers, IDE extensions, and autonomous agent systems (such as Pi Dev / pi.dev). Software engineers frequently jump between codebases and repositories to mitigate high-severity production incidents, participate in pull request reviews, resolve ad-hoc dependencies, or transition between sprints.

### The Core Problem
1. **Context Switch Blindness:** Tracking when, where, and why an engineer shifted attention away from their primary project requires manually correlating disconnected commit logs, branch checkouts, PR reviews, and issue status transitions.
2. **Cognitive Reconstitution Cost:** When returning to a project after days or weeks on hotfixes, developers waste substantial cognitive bandwidth reconstructing what feature was in flight, what branch was checked out, and why work stalled.
3. **Onboarding Lag:** New engineers or rotating contributors joining a codebase lack a consolidated, real-time status brief of active initiatives, unresolved blockers, and recent developer migrations.

### The DevTrace Solution
DevTrace solves this by:
- **Ingesting Multi-Source Telemetry:** Normalizes raw events from Git, Jira, and AI agents into a unified, queryable schema hosted on **Supabase**.
- **Declarative Context Switch Detection:** Applies **DSPy (v2.5+)** Chain-of-Thought reasoning powered by ultra-low-latency **Groq LPU** inference to analyze time-windowed activity logs, pinpointing exact project pivots and technical rationales (e.g., hotfix checkouts, P0 tickets).
- **Automated Onboarding Synthesis:** Aggregates trailing event histories to synthesize structured briefings containing active objectives, known blockers, and contributor movements.
- **Interactive Observability Hub:** Exposes a **Streamlit** dashboard for engineering leadership and developers to monitor cross-project shifts and review onboarding briefs in real time.

---

## 2. System Architecture & Workflow

DevTrace operates as an event-driven data and intelligence pipeline. The diagram below illustrates the end-to-end data lifecycle:

```text
+-----------------------------------------------------------------------------------+
|                            DEVELOPER ACTIVITY SOURCES                             |
|   +-------------------+    +----------------------+    +----------------------+   |
|   |   Git Telemetry   |    |    Jira Telemetry    |    |  Pi Agent Sessions   |   |
|   | (commits, check-  |    | (ticket transitions, |    | (sessions, tool      |   |
|   |  outs, reviews)   |    |  status, comments)   |    |  calls, completions) |   |
|   +---------+---------+    +----------+-----------+    +----------+-----------+   |
+-------------|-------------------------|---------------------------|---------------+
              |                         |                           |
              +-------------------------+---------------------------+
                                        |
                                        v
                    +---------------------------------------+
                    |       Synthetic Data Generator        |
                    |       (data/simulate_data.py)         |
                    |    Deterministic 14-day timeline      |
                    +-------------------+-------------------+
                                        |
                                        v [data/simulated_events.json]
                    +---------------------------------------+
                    |          Telemetry Ingestion          |
                    |        (src/ingest_supabase.py)       |
                    |   Normalizes keys & batch-inserts     |
                    +-------------------+-------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                              SUPABASE POSTGRES LAYER                              |
|   +---------------------------------------------------------------------------+   |
|   |                          developer_events                                 |   |
|   |   [timestamp | developer_id | project_id | source_tool | content | meta]   |   |
|   +---------------------------------------------------------------------------+   |
+---------------------------------------+-------------------------------------------+
                                        |
                                        v
                    +---------------------------------------+
                    |        DevTrace Pipeline Runner       |
                    |       (src/pipeline_runner.py)        |
                    +-------------------+-------------------+
                                        |
                         +--------------+--------------+
                         |                             |
                         v                             v
           +---------------------------+ +---------------------------+
           |    DetectContextSwitch    | |  SynthesizeOnboardingBrief |
           |  (dspy.ChainOfThought)    | |   (dspy.ChainOfThought)   |
           +-------------+-------------+ +-------------+-------------+
                         |                             |
                         +--------------+--------------+
                                        |
                                        v [Groq LPU / openai/gpt-oss-120b]
                         +--------------+--------------+
                         |                             |
                         v                             v
+-----------------------------------------------------------------------------------+
|                        SUPABASE PERSISTENCE & ANALYTICS                           |
|   +-----------------------------------+   +-----------------------------------+   |
|   |         context_switches          |   |     project_onboarding_briefs     |   |
|   |  - developer_id, switched_at      |   |  - project_id, generated_at       |   |
|   |  - from_project -> to_project     |   |  - active_objectives (JSONB)      |   |
|   |  - reason, confidence_score       |   |  - current_blockers (JSONB)       |   |
|   |  - detected_by                    |   |  - recent_switches (JSONB)        |   |
|   |                                   |   |  - raw_summary (TEXT)             |   |
|   +-----------------+-----------------+   +-----------------+-----------------+   |
+---------------------|---------------------------------------|---------------------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         STREAMLIT VISUALIZATION HUB (app.py)                      |
|   +-------------------------+ +-------------------------+ +-------------------+   |
|   |      Tab 1: Timeline    | |     Tab 2: Briefing     | |   Tab 3: Raw Logs |   |
|   | - Metric Cards          | | - Executive Summary     | | - Filter by dev   |   |
|   | - Switch Badges         | | - Active Objectives     | | - Filter by tool  |   |
|   | - AI Reasoning Rationale| | - Highlighted Blockers  | | - Real-time JSON  |   |
|   +-------------------------+ +-------------------------+ +-------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 3. Database Schema & Data Modeling

DevTrace stores raw events, detected transitions, and project briefs in PostgreSQL on Supabase (`db/schema.sql`):

### 1. `developer_events`
Stores normalized developer activities across tools.
```sql
CREATE TABLE IF NOT EXISTS developer_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    developer_id TEXT NOT NULL,
    source_tool TEXT NOT NULL,       -- 'git', 'jira', 'pi_agent', 'slack'
    project_id TEXT NOT NULL,        -- e.g., 'Project-Alpha', 'Project-Beta'
    event_type TEXT NOT NULL,        -- 'commit', 'checkout', 'ticket_transition', etc.
    content TEXT,                    -- Commit message, ticket summary, or action
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### 2. `context_switches`
Stores validated project context switches with confidence scores and technical rationales.
```sql
CREATE TABLE IF NOT EXISTS context_switches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    developer_id TEXT NOT NULL,
    switched_at TIMESTAMPTZ NOT NULL,
    from_project TEXT NOT NULL,
    to_project TEXT NOT NULL,
    reason TEXT,
    confidence_score REAL,
    detected_by TEXT
);
```

### 3. `project_onboarding_briefs`
Stores AI-synthesized status reports for onboarding developers.
```sql
CREATE TABLE IF NOT EXISTS project_onboarding_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    active_objectives JSONB DEFAULT '[]'::jsonb,
    current_blockers JSONB DEFAULT '[]'::jsonb,
    recent_switches JSONB DEFAULT '[]'::jsonb,
    raw_summary TEXT
);
```

---

## 4. Declarative DSPy Intelligence Engine

DevTrace uses **DSPy (v2.5+)** for prompt programming, modular signature design, and teleprompter optimization (`src/dspy_modules.py`).

### DSPy Signatures
1. **`DetectContextSwitch`**:
   - **Inputs**: `developer_id`, `prior_project`, `recent_events_summary`
   - **Outputs**:
     - `switch_detected: bool` — True if developer pivoted focus to another project.
     - `target_project: str` — The destination project.
     - `rationale: str` — Grounded technical explanation citing branch names, ticket IDs (e.g., `BETA-911`), or agent sessions.
     - `confidence: float` — Confidence score (0.0 to 1.0).

2. **`SynthesizeOnboardingBrief`**:
   - **Inputs**: `project_id`, `project_event_history`
   - **Outputs**:
     - `active_objectives: List[str]` — Current in-flight features and bug fixes.
     - `current_blockers: List[str]` — Failing tasks, blocked Jira tickets, or unresolved errors.
     - `recent_switches: List[str]` — Team members who transitioned into or out of the project.
     - `executive_summary: str` — High-level briefing for new developers.

### Composite Pipeline (`DevTraceEngine`)
Encapsulates both reasoning modules with Chain-of-Thought (`dspy.ChainOfThought`):
```python
class DevTraceEngine(dspy.Module):
    def __init__(self):
        super().__init__()
        self.detector = dspy.ChainOfThought(DetectContextSwitch)
        self.summarizer = dspy.ChainOfThought(SynthesizeOnboardingBrief)

    def detect_switch(self, developer_id: str, prior_project: str, recent_events_summary: str):
        return self.detector(...)

    def generate_brief(self, project_id: str, project_event_history: str):
        return self.summarizer(...)
```

### Model Optimization (`src/evaluate_optimizer.py`)
- Evaluates the detector against a benchmark of labeled switch and non-switch scenarios using a strict metric:
  $$\text{Metric} = (\text{pred.switch} == \text{ex.switch}) \land (\text{pred.target.lower()} == \text{ex.target.lower()} \text{ if switch else True})$$
- Uses `dspy.teleprompt.BootstrapFewShot` with `max_bootstrapped_demos=3` to compile demonstration traces into `compiled_devtrace.json`.

---

## 5. Telemetry Simulation (`data/simulate_data.py`)

DevTrace includes a deterministic data generator producing 14 days of chronological logs across three developers:
- `dev_sanket`
- `dev_alex`
- `dev_elena`

### The Context Switch Scenario
- **Day 1–4**: `dev_sanket` works on `Project-Alpha` (ticket updates, feature commits, unit tests).
- **Day 5**: An urgent P0 bug (`BETA-911`: memory leak in auth service) forces an explicit context switch to `Project-Beta`. `dev_sanket` checks out `hotfix/BETA-911-auth-leak` and transitions the ticket to `IN_PROGRESS`.
- **Day 7**: `dev_sanket` marks `BETA-911` as `DONE`.
- **Day 8**: `dev_sanket` checks out `feature/ALPHA-101-core-pipeline` and resumes work on `Project-Alpha`.

Run data generation:
```bash
python data/simulate_data.py
```
This produces 256 structured records in `data/simulated_events.json`.

---

## 6. End-to-End Pipeline Execution (`src/pipeline_runner.py`)

The pipeline runner orchestrates data ingestion, windowing, inference, and database persistence:
1. Queries `developer_events` from Supabase ordered by `timestamp ASC`.
2. Groups logs by developer and maintains a sliding window of recent activities.
3. Evaluates project transitions via `DevTraceEngine.detect_switch()`.
4. Writes detected switches to `context_switches`.
5. Synthesizes 14-day trailing event logs for each project via `DevTraceEngine.generate_brief()`.
6. Stores briefs in `project_onboarding_briefs`.

Run the automated pipeline:
```bash
python src/pipeline_runner.py
```

---

## 7. Interactive Streamlit Dashboard (`app.py`)

DevTrace provides a web-based dashboard built with Streamlit:

### Tab 1: Context Switch Timeline
- **High-Level Metric Bar**: Total Switches Detected, Unique Developers Tracked, Average Confidence.
- **Transition Cards**: Displays developer, timestamp, `From Project` &rarr; `To Project` badges, confidence rating, and the full model rationale.

### Tab 2: New Hire Project Briefing
- **Project Selector**: Dropdown to toggle between `Project-Alpha` and `Project-Beta`.
- **Structured Briefing**:
  - Executive Summary callout box.
  - Active Objectives bullet list.
  - Known Blockers alert banner.
  - Recent Contributor Switches list.

### Tab 3: Raw Telemetry & Trace
- Interactive filtering by developer ID and source tool (`git`, `jira`, `pi_agent`).
- Searchable data table with an expandable raw JSON viewer.

Launch the dashboard:
```bash
streamlit run app.py
```

---

## 8. Installation & Quickstart

### Prerequisites
- Python 3.11+ or 3.12+
- A Supabase project with database credentials
- A Groq API key

### 1. Clone & Install
```bash
git clone <repository-url>
cd devtrace
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Ensure `.env` contains:
```env
# Groq API Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
DSPY_MODEL=openai/gpt-oss-120b

# Supabase Credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Optional Direct Postgres URI
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.your-project.supabase.co:5432/postgres"
```

### 3. Initialize Database Tables
Execute the SQL schema in `db/schema.sql` via the Supabase SQL Editor.

### 4. Run the Full Workflow
```bash
# 1. Generate 14-day simulated developer events
python data/simulate_data.py

# 2. Ingest events into Supabase
python src/ingest_supabase.py

# 3. Execute the switch detection and briefing pipeline
python src/pipeline_runner.py

# 4. Launch the Streamlit dashboard
streamlit run app.py
```

---

## 9. Evaluation & Testing

Run unit tests:
```bash
pytest
```

Run the DSPy evaluation and optimization harness:
```bash
python src/evaluate_optimizer.py
```

---

## 10. Repository Structure

```text
devtrace/
├── app.py                         # Streamlit UI dashboard (3 tabs)
├── compiled_devtrace.json         # Compiled DSPy artifact with few-shot demonstrations
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Project dependencies
├── .env.example                   # Environment configuration template
├── README.md                      # Documentation
├── data/
│   ├── simulate_data.py           # Deterministic 14-day telemetry generator
│   └── simulated_events.json      # Generated telemetry dataset (256 events)
├── db/
│   └── schema.sql                 # PostgreSQL DDL for tables and indexes
├── src/
│   ├── __init__.py                # Package root
│   ├── config.py                  # Environment and model configuration
│   ├── dspy_modules.py            # DSPy Signatures and DevTraceEngine module
│   ├── evaluate_optimizer.py      # Self-contained evaluation harness & teleprompter
│   ├── ingest_supabase.py         # Batch ingestion script for Supabase
│   ├── pipeline_runner.py         # End-to-end pipeline runner
│   ├── test_run.py                # Verification test script
│   └── trace_loader.py            # Trace loader utility
├── tests/
│   ├── __init__.py                # Test package root
│   └── test_modules.py            # Unit test suite
└── workflows/
    └── n8n_pipeline_spec.md       # n8n ingestion pipeline specification
```

---

## License
MIT License. Free for commercial and research use.
