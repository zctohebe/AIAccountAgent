# AI Accounting Agent (Demo)

A demo for an AI-assisted accounting automation stack: task scheduling, pluggable report processing, Bedrock (or mock) model interaction, and a React + React-Bootstrap front-end.

## Directory Overview
- `backend/` 每 Python backend (Lambda style handler + local dev server)
- `backend/reports/` 每 Pluggable report handlers (`sample_summary.py`, `anomaly_check.py`)
- `backend/report_executor.py` 每 Unified report execution (local / optional S3 I/O)
- `frontend/` 每 React UI (single HTML file served statically, dark theme)
- `resources/` 每 Runtime data (tasks, notifications, scheduler state)
- `results/` 每 Generated outputs & report artifacts (ignored by git)
- `scripts/` 每 Helper scripts (`start_all.bat`, `local_scheduler.py`)
- `docs/presentation.md` 每 Slide content (convert with Pandoc or Marp)

## Key Features
| Feature | What | Demo Prompt / Action |
|---------|------|----------------------|
| Natural Language | Execute accounting intents via free?form text | `Generate invoice summary` |
| Task Scheduler | Create cron based tasks; auto reload JSON | `[Task Scheduler] cron=*/1 * * * * outputPath=results/quick-task.txt` |
| Task Status | View active scheduled jobs + task file entries | `[Task Status]` |
| Report Processing | Modular handlers discovered dynamically | `Run Sample Summary Report { "prompt": "[Run Report]", ... }` |
| Anomaly Detection | Flags negative amounts | Use `reportType: anomaly-check` |
| File Attachments | Upload multiple files; included as context | Use upload icon then Send |
| Markdown Responses | Backend returns `markdown` field for rich UI | Any prompt |

## Report Execution Examples
Summary:
```json
{
  "prompt": "[Run Report]",
  "reportType": "sample-summary",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/sample-summary-output.json" },
  "params": {}
}
```
Anomaly Check:
```json
{
  "prompt": "[Run Report]",
  "reportType": "anomaly-check",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/anomaly-check-output.json" },
  "params": {}
}
```
Switch to S3 by using `source: "s3"` and `path: "s3://bucket/key"` (requires valid AWS creds & boto3).

## Task Status Output (Improved)
`[Task Status]` returns markdown similar to:
```
## Scheduled Tasks Status

### Active Jobs
- ID: `task-20251127191818-74f286` 〞 Every minute (UTC)
...

### Tasks File Entries (first 10)
- ID: `task-20251128043649-347d5a`
  - Trigger: At 06:00 every day (UTC)
  - Prompt: Send the attached xlsx report to j2fan@163.com at 14:00 today Recipient: j2fan@163.com
  - Output: `results/task-20251128043649-347d5a-output.txt`
```
Cron expressions are humanized when possible (minute, hourly, daily, weekly patterns).

## File Attachments
Front?end upload icon allows multiple file attachments:
1. Click paperclip icon ↙ choose file(s) ↙ each uploaded to backend `/upload` ↙ stored in `UserStorage/`.
2. Attachment names appear with remove (℅) icon.
3. Sending a prompt includes `attachments` array in request body; backend can incorporate into model context.

## Backend Interaction
POST body structure (simplified):
```json
{
  "prompt": "Generate invoice summary",
  "attachments": [ { "name": "invoices.json", "path": "UserStorage/invoices.json" } ]
}
```
Response includes:
```json
{
  "ok": true,
  "model_response": "...raw or mock model output...",
  "markdown": "```\n...\n```"
}
```
`markdown` is preferred for UI rendering.

## Local Development (Windows)
Prerequisites: Python 3.9+, optional AWS creds for Bedrock & S3.

Quick start (one script):
```cmd
scripts\start_all.bat
```
This creates venv (if missing), installs dependencies, starts:
- Backend (http://localhost:8000)
- Frontend (http://localhost:8080) 每 React single page
- Local scheduler (cron reload every 30s)

Manual backend launch:
```cmd
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe handler.py
```
Frontend (static):
```cmd
cd frontend
python -m http.server 8080
```

## Bedrock & Mock Mode
Set in `env.json` or environment:
- `BEDROCK_MODEL_ID` (default `deepseek-chat:1.0` placeholder)
- `BEDROCK_MOCK=1` or `USE_MOCK_BEDROCK=true` for offline echo responses.
Bearer token invocation supported via `AWS_BEARER_TOKEN_BEDROCK` (skips normal AWS signing for demo).

## Adding a New Report Handler
1. Create `backend/reports/my_handler.py`:
```python
REPORT_TYPE = "trial-balance"

def process(ctx):
    data = ctx.get("data", [])
    return {"ok": True, "data": {"lines": len(data)}}
```
2. Use in prompt JSON with `"reportType": "trial-balance"`.
Discovery is automatic.

## Presentation / Slides
Convert `docs/presentation.md` to PPTX:
```bash
pandoc docs/presentation.md -o docs/presentation.pptx
pandoc docs/presentation.md -o docs/presentation.pptx --reference-doc=templates/template.pptx
```
Or Marp:
```bash
marp docs/presentation.md --pptx
```

## Cloud Migration Path
- Replace local scheduler with EventBridge Rule or Scheduler ↙ invokes Lambda
- Deploy report executor & handler as Lambda (ZIP/SAM) or ECS task
- Use S3 for inputs/outputs; SNS or EventBridge for notifications
- Persist structured result/metadata to DynamoDB or RDS

## Troubleshooting
| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Reinstall requirements inside venv |
| CORS error | Ensure backend running & `window.__API_BASE__` correct |
| Infinite reload | Hard refresh (Ctrl+F5); ensure no stray reload code |
| Cron not humanized | Pattern unsupported ↙ raw cron shown |

## Cleaning / Ignored Artifacts
Git ignores: virtual envs, `results/`, `resources/notifications.json`, `resources/scheduler_state.json`, `.vs/`, caches. Use `git rm --cached` for previously tracked artifacts.

## Security Notes
- Demo only: do not place sensitive data in `UserStorage/` or `resources/` without proper access controls.
- Add auth / HTTPS & signed URLs for production.

## License / Contributing
Demo starter; feel free to fork and extend. Open issues / PRs for improvements.
