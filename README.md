# AI Accounting Agent (Demo)

Simple demo project with a Python AWS Lambda backend (SAM) and a minimal frontend.

Overview

- `backend/` — Python Lambda function and a small local dev HTTP server (`backend/handler.py`).
- `scripts/` — Dev helpers. Includes `local_scheduler.py` to run cron-like tasks locally.
- `backend/reports/` — Pluggable report handlers (`sample_summary.py`, `anomaly_check.py`).
- `backend/report_executor.py` — Unified entry to run reports (local/S3 input, local/S3 output).
- `template.yaml` — AWS SAM template for deploying the Lambda function.
- `docs/presentation.md` — Presentation script to convert into PPT.

Local development (Windows)

Use a single starter script to launch backend, frontend, and scheduler.

Prerequisites

- Python 3.9+ and `pip`.
- (Optional) AWS SAM CLI and Docker if you want to run `sam local`.

Start everything

From repository root run:

```cmd
.\scripts\start_all.bat
```

Windows opens:
- Backend: `http://localhost:8000` (runs `backend/handler.py`).
- Frontend: serves `frontend/` on port 8080 (if folder exists).
- Scheduler: `scripts/local_scheduler.py`.

Key features (demo)

- Natural language command
  - Example: `生成发票汇总`
- Scheduled task
  - Example: `[Task Scheduler] cron=*/1 * * * * outputPath=results/quick-task.txt`
- Run report
  - Example 1 (summary):
```
{
  "prompt": "[Run Report]",
  "reportType": "sample-summary",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/sample-summary-output.json" },
  "params": {}
}
```
  - Example 2 (anomaly):
```
{
  "prompt": "[Run Report]",
  "reportType": "anomaly-check",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/anomaly-check-output.json" },
  "params": {}
}
```
- Multi-source data
  - Local JSON/JSONL; switchable to S3 via `source: "s3"` and `path: "s3://bucket/key"`
- Automatic result storage
  - Outputs in `results/*.json` and `results/*.txt`, notifications in `resources/notifications.json`

Usage

- `[Task Status]` — list current jobs and tasks.
- `[Task Scheduler]` — create a scheduled task via prompt parameters `cron=... outputPath=...`.
- `[Run Report]` — run a report; send JSON payload as above or embed the JSON inside the prompt.

Environment

- Edit `env.json` for AWS/BEDROCK settings.
- To mock Bedrock: set `"BEDROCK_MOCK": "1"` or `"USE_MOCK_BEDROCK": "true"`.

Cloud migration

- EventBridge/Scheduler triggers Lambda for tasks.
- Report executor as Lambda/ECS.
- S3 inputs/outputs; SNS/CloudWatch for notifications.
