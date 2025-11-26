# AI Accounting Agent (Demo)

Simple demo project with a Python AWS Lambda backend (SAM) and a minimal frontend.

Overview

- `backend/` ¡ª Python Lambda function and a small local dev HTTP server (`backend/handler.py`).
- `frontend/` ¡ª Static single-page UI (`index.html`, `app.js`, `styles.css`).
- `template.yaml` ¡ª AWS SAM template for deploying the Lambda function.

Local development (Windows)

We provide a single Windows starter script to launch backend and frontend for development.

Prerequisites

- Python 3.9+ and `pip`.
- (Optional) AWS SAM CLI and Docker if you want to run `sam local`.

Start everything

From repository root run:

```powershell
.\scripts\start_all.ps1
```

This opens two PowerShell windows: one for the backend (runs `backend/handler.py`) and one for the frontend (serves `frontend/` on port 8080). The frontend is available at `http://localhost:8080` and the backend at `http://localhost:8000`.

Environment

- Edit `env.json` in repository root to provide `BEDROCK_MODEL_ID`, `UPLOAD_BUCKET`, and `AWS_REGION` for local testing with real AWS resources.

S3 upload / presign flow (local dev)

- The frontend requests a presigned POST from `POST /presign` with JSON `{ "filename": "...", "content_type": "..." }`.
- The backend returns presigned fields and URL. Frontend uploads directly to S3 with a form POST.
- For local development, if no `UPLOAD_BUCKET` environment variable is set, the backend returns a mock presign response and the file upload step will be skipped.

Deploy to AWS

- The SAM template expects an `UploadBucketName` parameter. Create an S3 bucket and deploy with:

```bash
sam build
sam deploy --guided
# Provide BedrockModelId and UploadBucketName when prompted
```

Contributing

This is a demo starter; feel free to open issues or PRs to improve.
