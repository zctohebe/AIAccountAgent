import os
import sys
import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import uuid
from urllib.parse import quote
import base64
import re

# Ensure repository root on sys.path for imports when running directly
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Optional external dependencies
try:
    import requests  # for bearer token flow (not mandatory)
except Exception:
    requests = None

# Import report executor (used for [Run Report])
try:
    from backend.report_executor import execute as execute_report
except Exception:
    execute_report = None

# Logger setup
logger = logging.getLogger("handler")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_h)

# Configuration loading from env.json (if present)
config = {}
ENV_JSON = os.path.join(REPO_ROOT, 'env.json')
if os.path.exists(ENV_JSON):
    try:
        with open(ENV_JSON, 'r', encoding='utf-8') as f:
            config = json.load(f) or {}
        logger.info('Loaded configuration from env.json')
    except Exception as e:
        logger.warning('Failed to load env.json: %s', e)


def _cfg(key, default=''):
    if key in config:
        return config.get(key, default)
    return os.environ.get(key, default)


def _bool_cfg(key, default=False):
    val = _cfg(key, None)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('1', 'true', 'yes', 'on')
    try:
        return bool(int(val))
    except Exception:
        return default

AWS_ACCESS_KEY_ID = _cfg('AWS_ACCESS_KEY_ID') or ''
AWS_SECRET_ACCESS_KEY = _cfg('AWS_SECRET_ACCESS_KEY') or ''
AWS_SESSION_TOKEN = _cfg('AWS_SESSION_TOKEN') or ''
AWS_REGION = _cfg('AWS_REGION') or 'us-east-1'
BEDROCK_MODEL_ID = _cfg('BEDROCK_MODEL_ID') or 'deepseek-chat:1.0'

RESULTS_DIR = os.path.join(REPO_ROOT, 'results')
RESOURCES_DIR = os.path.join(REPO_ROOT, 'resources')
USER_STORAGE_DIR = os.path.join(REPO_ROOT, 'UserStorage')
TASKS_PATH = os.path.join(REPO_ROOT, 'tasks.json')
TASKS_FALLBACK_PATH = os.path.join(RESOURCES_DIR, 'tasks.json')
SCHEDULER_STATE_PATH = os.path.join(RESOURCES_DIR, 'scheduler_state.json')
NOTIFICATIONS_PATH = os.path.join(RESOURCES_DIR, 'notifications.json')


def _ensure_parent_dir(path: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass


def _extract_bearer_token(raw: str) -> str:
    if not raw:
        return ''
    token = raw.strip()
    if token.startswith('AWS_BEARER_TOKEN_BEDROCK='):
        token = token.split('=', 1)[1]
    if token.lower().startswith('bearer '):
        token = token.split(' ', 1)[1]
    return token.strip()


def _invoke_with_bearer(model_id: str, payload: dict, token: str):
    if not requests:
        return {"ok": False, "model_response": f"(mock) echo: {payload['messages'][-1]['content']}"}
    token = _extract_bearer_token(token)
    if not token:
        return {"ok": False, "model_response": f"(mock) echo: {payload['messages'][-1]['content']}"}
    encoded_model = quote(model_id, safe='')
    url = f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com/model/{encoded_model}/invoke"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=60)
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return {"ok": True, "model_response": body}
    except Exception as e:
        logger.warning('Bearer invocation failed: %s', e)
        return {"ok": False, "model_response": f"(mock) echo: {payload['messages'][-1]['content']}", "error": str(e)}


def call_bedrock(prompt: str):
    """Invoke Bedrock or return mock if not available. Removes previous garbled strings."""
    # Mock mode
    if _bool_cfg('BEDROCK_MOCK') or _bool_cfg('USE_MOCK_BEDROCK') or os.environ.get('BEDROCK_MOCK') == '1':
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    payload = {
        "messages": [{"role": "你是一个AI会计助手", "content": prompt}],
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 500
    }

    bearer_raw = _cfg('AWS_BEARER_TOKEN_BEDROCK') or os.environ.get('AWS_BEARER_TOKEN_BEDROCK', '')
    if bearer_raw:
        return _invoke_with_bearer(BEDROCK_MODEL_ID, payload, bearer_raw)

    client = None
    try:
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            client = boto3.client('bedrock-runtime',
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                  aws_session_token=AWS_SESSION_TOKEN or None,
                                  region_name=AWS_REGION)
        else:
            client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        logger.info('Created bedrock-runtime client')
    except Exception as e:
        logger.warning('Failed to create bedrock-runtime client: %s', e)
        try:
            client = boto3.client('bedrock', region_name=AWS_REGION)
            logger.info('Created legacy bedrock client')
        except Exception as e2:
            logger.warning('Could not create any Bedrock client: %s', e2)
            return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        resp = client.invoke_model(modelId=BEDROCK_MODEL_ID, contentType="application/json", body=json.dumps(payload))
        raw = resp['body'].read().decode('utf-8')
        return {"ok": True, "model_response": raw}
    except Exception as e:
        logger.warning('Bedrock invocation failed: %s', e)
        return {"ok": False, "error": str(e), "model_response": f"(mock) echo: {prompt}"}


def _read_json(path: str, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, obj):
    _ensure_parent_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _append_notification(message: dict):
    existing = _read_json(NOTIFICATIONS_PATH, [])
    existing.append(message)
    _write_json(NOTIFICATIONS_PATH, existing)


def _find_tasks_file() -> str:
    return TASKS_PATH if os.path.exists(TASKS_PATH) else TASKS_FALLBACK_PATH


def _list_tasks():
    state = _read_json(SCHEDULER_STATE_PATH, {})
    jobs = state.get('jobs', {})
    tasks_path = _find_tasks_file()
    tasks = _read_json(tasks_path, [])
    return {"jobs": jobs, "tasks": tasks, "source": tasks_path}


def _cron_humanize(expr: str) -> str:
    expr = (expr or '').strip()
    if expr in ('* * * * *', '*/1 * * * *'):
        return 'Every minute (UTC)'
    if expr == '0 * * * *':
        return 'At minute 0 of every hour (UTC)'
    m = re.match(r'^(\d{1,2}) (\d{1,2}) \* \* \*$', expr)
    if m:
        minute, hour = int(m.group(1)), int(m.group(2))
        return f'At {hour:02d}:{minute:02d} every day (UTC)'
    m2 = re.match(r'^(\d{1,2}) (\d{1,2}) \* \* (\d)$', expr)
    if m2:
        minute, hour, dow = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
        day = days[dow] if 0 <= dow <= 6 else f'day {dow}'
        return f'At {hour:02d}:{minute:02d} every {day} (UTC)'
    if re.match(r'^\*/\d+ \* \* \* \*$', expr):
        n = int(expr.split()[0].split('/')[1])
        return f'Every {n} minute(s) (UTC)'
    if re.match(r'^\d{1,2} \*/\d+ \* \* \*$', expr):
        parts = expr.split()
        minute = parts[0]
        hours = int(parts[1].split('/')[1])
        return f'At minute {minute} every {hours} hour(s) (UTC)'
    return f'Cron: `{expr}` (UTC)'


def _format_task_status_md(status: dict) -> str:
    lines = ["## Scheduled Tasks Status", ""]
    jobs = status.get('jobs', {})
    tasks = status.get('tasks', [])
    if jobs:
        lines.append("### Active Jobs")
        for tid, meta in jobs.items():
            cron_expr = meta.get('cron', '')
            human = _cron_humanize(cron_expr)
            lines.append(f"- ID: `{tid}` — {human}")
        lines.append("")
    else:
        lines.append("- No scheduled jobs found.")
        lines.append("")
    if tasks:
        lines.append("### Tasks File Entries (first 10)")
        for t in tasks[:10]:
            tid = t.get('taskId')
            cron_expr = t.get('cron') or ''
            human = _cron_humanize(cron_expr)
            prompt = (t.get('prompt') or '').strip().replace('\n', ' ')
            lines.append(f"- ID: `{tid}`\n  - Trigger: {human}\n  - Prompt: {prompt}\n  - Output: `{t.get('outputPath','')}`")
    lines.append("")
    return "\n".join(lines)


def _create_task_from_prompt(prompt: str):
    cron = "*/1 * * * *"
    output_path = None
    for part in prompt.split():
        if part.startswith("cron="):
            cron = part.split("=", 1)[1]
        if part.startswith("outputPath="):
            output_path = part.split("=", 1)[1]
    task_id = "task-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    if not output_path:
        output_path = f"results/{task_id}-output.txt"
    new_task = {"taskId": task_id, "cron": cron, "enabled": True, "prompt": prompt, "outputPath": output_path}
    tasks_path = _find_tasks_file()
    tasks = _read_json(tasks_path, [])
    tasks.append(new_task)
    _write_json(tasks_path, tasks)
    _append_notification({"timestamp": datetime.utcnow().isoformat() + "Z", "taskId": task_id, "message": f"Task {task_id} created", "ok": True})
    return new_task, tasks_path


def _extract_embedded_json(text: str):
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    return None


def lambda_handler(event, context):
    body = event.get("body") if isinstance(event, dict) else None
    if isinstance(body, str):
        try:
            data = json.loads(body)
        except Exception:
            data = {"prompt": body}
    else:
        data = body or {}

    prompt = data.get("prompt", "Hello from AI Accounting Agent")
    normalized = prompt.strip()

    if "[Task Status]" in normalized:
        status = _list_tasks()
        md = _format_task_status_md(status)
        return {"statusCode": 200, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}, "body": json.dumps({"ok": True, "status": status, "markdown": md})}

    if "[Task Sceduler]" in normalized or "[Task Scheduler]" in normalized:
        new_task, src = _create_task_from_prompt(prompt)
        md = f"## Task Created\n\n- ID: `{new_task['taskId']}`\n- Cron: `{new_task['cron']}`\n- Output: `{new_task['outputPath']}`\n- Tasks file: `{src}`\n"
        return {"statusCode": 200, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}, "body": json.dumps({"ok": True, "message": "Task created", "task": new_task, "tasksFile": src, "markdown": md})}

    if "[Run Report]" in normalized and execute_report:
        embedded = _extract_embedded_json(prompt)
        payload = embedded if isinstance(embedded, dict) else data
        report_event = {"reportType": payload.get("reportType"), "input": payload.get("input", {}), "output": payload.get("output", {}), "params": payload.get("params", {}), "taskId": payload.get("taskId", "ui-report")}
        result = execute_report(report_event)
        md = f"## Report Executed\n\n- Type: `{result.get('reportType')}`\n- Output: `{result.get('outputPath')}`\n- OK: `{result.get('ok')}`\n"
        return {"statusCode": 200, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}, "body": json.dumps({"ok": True, "report": result, "markdown": md})}

    result = call_bedrock(prompt)
    # Build markdown without 'Model Response' heading
    md = "```\n" + str(result.get('model_response', '')) + "\n```"
    return {"statusCode": 200, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}, "body": json.dumps({**result, "markdown": md})}


# Local dev server
if __name__ == "__main__":
    class DevHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            event = {"body": body.decode('utf-8')}
            resp = lambda_handler(event, None)
            self.send_response(resp['statusCode'])
            for k, v in resp.get('headers', {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp['body'].encode('utf-8'))

    logger.info('Starting local dev server at http://0.0.0.0:8000 (POST /)')
    HTTPServer(('0.0.0.0', 8000), DevHandler).serve_forever()