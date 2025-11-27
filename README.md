# AI Accounting Agent (Demo)
Simple demo project with a Python AWS Lambda backend (SAM) and a minimal frontend.

Overview

- `backend/` �� Python Lambda function and a small local dev HTTP server (`backend/handler.py`).
- `frontend/` �� Static single-page UI (`index.html`, `app.js`, `styles.css`).
- `template.yaml` �� AWS SAM template for deploying the Lambda function.

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
=======
# AIAccountAgent — 本地开发说明（中文）

本说明文档包含在 Windows 环境下启动和调试本项目的后端与前端的详细步骤、常用命令与排查建议。可复制粘贴 PowerShell 命令直接执行。

前置条件
- Windows + PowerShell
- Python 3.9 及以上（已添加到 PATH）
- （可选）GitHub CLI `gh`（若需要自动发布到 GitHub）

仓库结构（相关）
- `backend/`：后端代码（包含用于本地调试的 handler）
- `frontend/`：前端静态文件（HTML/JS/CSS）
- `scripts/`：辅助脚本（发布、同步远程分支等）

后端（开发服务器）快速启动

1) 进入后端目录：

```powershell
cd D:\workspace\AIAccountAgent\backend
```

2) 创建虚拟环境并安装依赖（仅需第一次）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

说明：如果无法运行 `Activate.ps1`（PowerShell 执行策略导致），可直接使用上面方式不激活虚拟环境。

3) 启动后端服务：

```powershell
.\.venv\Scripts\python.exe handler.py
```

- 默认监听 `http://0.0.0.0:8000`。启动成功后终端会有日志输出。

前端（静态）快速启动

1) 在另一个终端启动静态服务器：

```powershell
cd D:\workspace\AIAccountAgent\frontend
python -m http.server 8080
```

2) 在浏览器打开：

```
http://localhost:8080
```

- 前端默认通过 `window.__API_BASE__` 指向后端（`http://localhost:8000`），如需更改，请在 `frontend/index.html` 中修改或在页面加载前设置该变量。

测试后端接口

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -Body '{"prompt":"Hello"}' -ContentType 'application/json'
```

或：

```powershell
curl -Method POST -Uri http://localhost:8000/chat -Body '{"prompt":"Hello"}' -ContentType 'application/json'
```

停止服务与释放端口

- 在对应终端按 `Ctrl+C` 停止服务。
- 若端口未被释放，可查找占用进程并结束（示例为端口 8000）：

```powershell
$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($p) { Stop-Process -Id $p -Force }
```

常见问题与排查

- 前端不停刷新且日志反复出现 `304 Not Modified`：
  - 原因：工程里曾有一条 `location.reload()` 导致无限刷新（已移除）。若仍出现刷新：
    - 在浏览器强制刷新（Ctrl+F5）或清理缓存；
    - 在无痕/隐身窗口打开，排除缓存影响；
    - 检查 `frontend/index.html`、`frontend/app.js` 中是否有自动刷新或循环重载的代码。

- 无法激活 venv（PowerShell 执行策略提示）：
  - 解决：使用 venv 里的 python 直接运行命令，或临时放宽当前会话执行策略：
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1
    ```

- 缺少 Python 依赖（例如 `ModuleNotFoundError: No module named 'boto3'`）：
  - 解决：进入后端目录，使用 venv 的 pip 安装依赖 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`。

- 前端访问后端报 CORS 错误：
  - 本项目后端在开发环境返回 `Access-Control-Allow-Origin: *`，如仍报错请确认 `window.__API_BASE__` 指向运行中的后端并重启后端。

开发建议

- 如想避免跨域和端口管理问题，可将前端静态文件交由后端提供（即后端同时托管静态资源），我可以帮你更新 `handler.py` 实现该功能；这样访问 `http://localhost:8000` 即可同时获得前端与 API。 
- 项目中已有若干辅助脚本（`scripts/`）可用于发布到 GitHub、同步远程分支等。

需要帮助？

如果你遇到无法解决的问题，请把终端输出、浏览器控制台（Console）与网络请求（Network）中的错误信息直接粘贴到这里，我会逐步协助你排查并修复。
# AIAccountAgent — Local Development

This README explains how to start the backend (Python Lambda-mock dev server) and the frontend (static files) locally on Windows, with copy-paste PowerShell commands and troubleshooting tips.

Prerequisites
- Windows with PowerShell
- Python 3.9+ installed and available on PATH
- (optional) `gh` CLI if you want to publish to GitHub from scripts

Repository layout (relevant parts)
- `backend/` — Python backend (dev server / Lambda handler)
- `frontend/` — Static UI (HTML/JS/CSS)
- `scripts/` — helper scripts (publish, sync branches, etc.)

Quickstart — Backend (dev server)

1. Open PowerShell and change to backend folder:

```powershell
cd D:\workspace\AIAccountAgent\backend
```

2. Create a virtual environment (if not yet created) and install dependencies:

```powershell
# create venv (only once)
python -m venv .venv

# Use the venv python to install dependencies (no need to "Activate" if execution policy blocks scripts)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Start the backend dev server:

```powershell
.\.venv\Scripts\python.exe handler.py
```

- The dev server listens on `0.0.0.0:8000` by default. You should see log lines when it starts.
- If you prefer activating the venv (PowerShell) and it is blocked by execution policy, either:
  - Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that session, then `.\.venv\Scripts\Activate.ps1`; or
  - Continue using the venv's python directly as shown above.

Quickstart — Frontend (static)

1. Open a second PowerShell window and serve the `frontend/` directory with Python's simple HTTP server:

```powershell
cd D:\workspace\AIAccountAgent\frontend
python -m http.server 8080
```

2. Open the UI in your browser:

```
http://localhost:8080
```

- The frontend is configured to call the backend at `http://localhost:8000` via `window.__API_BASE__` in `index.html`.
- If you change the backend host/port, update `window.__API_BASE__` in `frontend/index.html` or set it before the page loads.

Testing API connectivity

From any terminal, you can POST to the dev server:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -Body '{"prompt":"Hello"}' -ContentType 'application/json'
```

Or using curl (PowerShell alias):

```powershell
curl -Method POST -Uri http://localhost:8000/chat -Body '{"prompt":"Hello"}' -ContentType 'application/json'
```

Stopping services

- In the terminal where the backend or frontend is running, press `Ctrl+C` to stop the server.
- If a process still holds a port (e.g. 8000/8080), find the PID and kill it:

```powershell
# find and stop process using port 8000
$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($p) { Stop-Process -Id $p -Force }
```

Troubleshooting

- Repeated `304 Not Modified` logs and infinite page reload:
  - This project previously had an unconditional `location.reload()` in `frontend/index.html` which caused an infinite reload loop and repeated `GET /` logs returning `304`. That line has been removed. If you still see reloads:
    - Do a hard refresh in your browser (Ctrl+F5) to clear cached scripts.
    - Clear browser cache (or open an incognito window).
    - Ensure `frontend/index.html` does not include `location.reload()` or other reload logic.

- PowerShell cannot run `Activate.ps1`: execution policy error
  - Use the venv python directly (`.\.venv\Scripts\python.exe ...`) or temporarily set execution policy for the session:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1
    ```

- `ModuleNotFoundError: No module named 'boto3'` (or other missing modules)
  - Make sure you've installed dependencies into the venv with pip (see Quickstart backend step 2).

- CORS errors when front-end calls back-end
  - The dev server returns `Access-Control-Allow-Origin: *` in responses. If you still get CORS errors, confirm you are calling the correct backend `window.__API_BASE__` and that the backend process is the one you started.

Development notes / next steps

- To avoid CORS and port mismatches you can host the frontend from the backend dev server. Ask me and I can add a simple static file handler to the backend so everything is available at `http://localhost:8000`.
- Helper scripts are available in `scripts/` for publishing to GitHub and syncing branches.

If anything fails, copy the exact terminal output and the browser console/network errors and paste them here; I'll help you debug step-by-step.
