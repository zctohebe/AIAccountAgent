# AI Accounting Agent

## Cover
- Theme: AI-powered Business Process Automation
- Title: AI Accounting Agent
- Team: Guardians of Gal (Leader: Zhan, Changlian)
- Business Area: Accounting

## Problem & Goals
- Reduce manual work and errors
- Improve efficiency and flexibility
- Cost savings and faster processing

## Architecture Overview
- Task Scheduling: Local PoC + AWS EventBridge/Amazon Scheduler -> Lambda
- Report Processing: Pluggable handlers -> Lambda/ECS
- AI Analysis: AWS Bedrock (mockable locally)
- Storage: S3 or local filesystem
- UI/API: Natural language commands

## Key Features (with demo samples)
- Natural Language Command Execution
  - Demo: "生成发票汇总"
- Scheduled Task Execution
  - Demo: UI prompt "[Task Scheduler] cron=*/1 * * * * outputPath=results/quick-task.txt"
- Multi-Source Data Integration
  - Demo: Report input from `resources/sample-data.jsonl` (switchable to S3)
- Automatic Result Storage
  - Demo: Outputs in `results/*.json` and `results/*.txt`
- Custom Rule Management
  - Demo: Add `backend/reports/anomaly_check.py` and use `reportType: anomaly-check`
- Intelligent Anomaly Detection
  - Demo: Detect `amount<0` -> list anomalies
- Secure Data Processing
  - Demo: Use mock Bedrock in dev, no sensitive data

## Demo Flow
1) Start: `scripts/start_all.bat`
2) Scheduler: reads `resources/tasks.json` (UTC cron)
3) UI commands:
   - `[Task Status]` -> list jobs and tasks
   - `[Task Scheduler] cron=*/1 * * * * outputPath=results/quick-task.txt` -> create task
   - `[Run Report]` with JSON payload (see examples)
4) Check outputs: `results/*`, notifications in `resources/notifications.json`

## Run Report Examples
- Sample Summary
```
{
  "prompt": "[Run Report]",
  "reportType": "sample-summary",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/sample-summary-output.json" },
  "params": {}
}
```
- Anomaly Check
```
{
  "prompt": "[Run Report]",
  "reportType": "anomaly-check",
  "input": { "source": "local", "format": "jsonl", "path": "resources/sample-data.jsonl" },
  "output": { "target": "local", "path": "results/anomaly-check-output.json" },
  "params": {}
}
```

## Cloud Migration Path
- Replace local scheduler with EventBridge rules
- Deploy report executor as Lambda/ECS
- Use S3 for inputs/outputs, SNS/CloudWatch for notifications

## Next Steps
- Add S3 integration in scheduler and UI
- Expand report handlers (trial balance, AR/AP aging)
- Add monitoring/alerts and IAM hardening
