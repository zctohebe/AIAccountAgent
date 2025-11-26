# AI Accounting Agent (Demo)

Simple demo project with a Python AWS Lambda backend (SAM) and a minimal frontend.

Overview

- `backend/` ¡ª Python Lambda function and a small local dev HTTP server (`backend/handler.py`).
- `frontend/` ¡ª Static single-page UI (`index.html`, `app.js`, `styles.css`).
- `template.yaml` ¡ª AWS SAM template for deploying the Lambda function.

Local development

Prerequisites

- Python 3.9+ and `pip`.
- Node.js / a static file server (optional) or any simple HTTP server to serve `frontend/`.
- (Optional) AWS SAM CLI to deploy using `template.yaml`.

Start backend locally

PowerShell:

```powershell
# from repository root
pip install -r backend/requirements.txt
python backend/handler.py
```

Start frontend locally

Option 1: Use a simple static server (Node.js `http-server`):

```bash
npm install -g http-server
cd frontend
http-server -c-1
```

Option 2: Use Python's simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```

Configuration

- By default the frontend expects the backend at `http://localhost:8000`. Adjust `window.__API_BASE__` in `frontend/index.html` or set a reverse proxy.

Deploy to AWS

- Use the `template.yaml` with SAM CLI: `sam build && sam deploy --guided` and provide `BedrockModelId`.

Contributing

This is a demo starter; feel free to open issues or PRs to improve.
