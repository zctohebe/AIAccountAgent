import os
import sys
import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote
from datetime import datetime
import uuid

# Ensure repository root on sys.path so 'backend' package is importable when running handler directly
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    import requests
except Exception:
    requests = None

from backend.report_executor import execute as execute_report

boto3.set_stream_logger('botocore', level='DEBUG')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

config = {}
try:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_json_path = os.path.join(repo_root, 'env.json')
    if os.path.exists(env_json_path):
        with open(env_json_path, 'r', encoding='utf-8') as f:
            config = json.load(f) or {}
        logger.info(f'Loaded configuration from {env_json_path}')
        if isinstance(config, dict) and 'ChatFunction' in config and isinstance(config['ChatFunction'], dict):
            cf = config['ChatFunction']
            for k, v in cf.items():
                if k not in config:
                    config[k] = v
except Exception as e:
    logger.warning('Failed to load env.json: %s', e)

RESULTS_DIR = os.path.join(repo_root, 'results')
RESOURCES_DIR = os.path.join(repo_root, 'resources')
TASKS_PATH = os.path.join(repo_root, 'tasks.json')
TASKS_FALLBACK_PATH = os.path.join(RESOURCES_DIR, 'tasks.json')
SCHEDULER_STATE_PATH = os.path.join(RESOURCES_DIR, 'scheduler_state.json')
NOTIFICATIONS_PATH = os.path.join(RESOURCES_DIR, 'notifications.json')


def _ensure_parent_dir(path: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass


def _find_tasks_path() -> str:
    return TASKS_PATH if os.path.exists(TASKS_PATH) else TASKS_FALLBACK_PATH


def _cfg(key, default=''):
    if isinstance(config, dict) and key in config:
        return config.get(key)
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

aws_access_key_id = _cfg('AWS_ACCESS_KEY_ID') or ''
aws_secret_access_key = _cfg('AWS_SECRET_ACCESS_KEY') or ''
aws_session_token = _cfg('AWS_SESSION_TOKEN') or ''
region_name = _cfg('AWS_REGION') or 'us-east-1'

if isinstance(region_name, str) and region_name.strip().lower() in ('global', 'none', 'default'):
    logger.warning("AWS_REGION is set to '%s' — mapping to 'us-east-1' for Bedrock calls", region_name)
    region_name = 'us-east-1'


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
        msg = "requests library not available. Install with: pip install requests"
        logger.error(msg)
        return {"ok": False, "error": msg, "model_response": "(mock) echo: " + payload.get("messages", [{}])[-1].get("content", "")}

    token = _extract_bearer_token(token)
    if not token:
        msg = "Empty bearer token"
        logger.error(msg)
        return {"ok": False, "error": msg, "model_response": "(mock) echo: " + payload.get("messages", [{}])[-1].get("content", "")}

    encoded_model = quote(model_id, safe='')
    url = f"https://bedrock-runtime.{region_name}.amazonaws.com/model/{encoded_model}/invoke"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    logger.info("Invoking Bedrock via HTTP Bearer at %s", url)
    try:
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=60)
        try:
            resp.raise_for_status()
        except requests.HTTPError as he:
            body = resp.text
            logger.error("HTTP Bearrock returned %s: %s", resp.status_code, body)
            try:
                logger.debug('Response headers: %s', dict(resp.headers))
            except Exception:
                pass
            return {"ok": False, "error": f"HTTP {resp.status_code}: {he}", "model_response": body, "response_headers": dict(resp.headers)}

        try:
            body_json = resp.json()
            logger.debug('Response headers: %s', dict(resp.headers))
            return {"ok": True, "model_response": body_json, "response_headers": dict(resp.headers)}
        except Exception:
            logger.debug('Response headers: %s', dict(resp.headers))
            return {"ok": True, "model_response": resp.text, "response_headers": dict(resp.headers)}
    except Exception as e:
        logger.exception("HTTP Bearer Bedrock invocation failed")
        return {"ok": False, "error": str(e), "model_response": "(mock) echo: " + payload.get("messages", [{}])[-1].get("content", "")}


def call_bedrock(prompt: str):
    model_id = _cfg('BEDROCK_MODEL_ID') or os.environ.get("BEDROCK_MODEL_ID", "deepseek-chat:1.0")

    if _bool_cfg('BEDROCK_MOCK') or _bool_cfg('USE_MOCK_BEDROCK') or os.environ.get('BEDROCK_MOCK') == '1':
        logger.info('Mock mode enabled via configuration; returning mock response without calling AWS')
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    payload = {
        "messages": [
            {
                "role": "你是一个AI会计助手",
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 500
    }

    bearer_raw = _cfg('AWS_BEARER_TOKEN_BEDROCK') or os.environ.get('AWS_BEARER_TOKEN_BEDROCK', '')
    bearer_token = _extract_bearer_token(bearer_raw)
    if bearer_token:
        logger.info("Detected AWS_BEARER_TOKEN_BEDROCK — using HTTP Bearer invocation")
        return _invoke_with_bearer(model_id, payload, bearer_token)

    client = None
    try:
        if aws_access_key_id and aws_secret_access_key:
            client = boto3.client(
                service_name='bedrock-runtime',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token or None,
                region_name=region_name,
            )
            logger.info('Created Bedrock runtime client using provided AWS_ACCESS_KEY_ID')
        else:
            client = boto3.client('bedrock-runtime', region_name=region_name)
            logger.info('Created Bedrock runtime client using default credential chain')
    except Exception as e:
        logger.warning('Failed to create bedrock-runtime client: %s', e)
        try:
            client = boto3.client('bedrock', region_name=region_name)
            logger.info('Created legacy Bedrock client')
        except Exception as e2:
            client = None
            logger.warning('Could not create any Bedrock client: %s', e2)

    if client is None:
        logger.warning("No Bedrock client available; returning mock response")
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(payload))
        output = resp['body'].read().decode('utf-8')
        print("模型输出：", output)
        body = None
        if isinstance(resp, dict):
            body = resp.get("body") or resp.get("Body") or resp
        else:
            body = resp
        try:
            if isinstance(body, (bytes, bytearray)):
                text = body.decode("utf-8")
            else:
                text = json.dumps(body)
        except Exception:
            text = str(body)
        return {"ok": True, "model_response": text}
    except Exception as e:
        err_str = str(e)
        if 'UnrecognizedClientException' in err_str or 'The security token included in the request is invalid' in err_str:
            logger.error('Bedrock invocation failed due to invalid credentials: %s', err_str)
            guidance = (
                'Invalid AWS credentials. To call Bedrock without running `aws login`, set the '
                'environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (and AWS_SESSION_TOKEN if needed), '
                'or set BEDROCK_MOCK=1 or USE_MOCK_BEDROCK=true to use local mock responses. You can also put these values into env.json in the repository root.'
            )
            logger.error(guidance)
            return {"ok": False, "error": err_str, "model_response": f"(mock) echo: {prompt}", "guidance": guidance}

        logger.exception("Bedrock invocation failed")
        return {"ok": False, "error": err_str, "model_response": f"(mock) echo: {prompt}"}


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
    new_task = {
        "taskId": task_id,
        "cron": cron,
        "enabled": True,
        "prompt": prompt,
        "outputPath": output_path
    }
    tasks_path = _find_tasks_file()
    tasks = _read_json(tasks_path, [])
    tasks.append(new_task)
    _write_json(tasks_path, tasks)
    _append_notification({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "taskId": task_id,
        "message": f"Task {task_id} created with cron '{cron}'",
        "ok": True,
        "outputPath": output_path,
    })
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
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"ok": True, "status": status}),
        }

    if "[Task Sceduler]" in normalized or "[Task Scheduler]" in normalized:
        new_task, src = _create_task_from_prompt(prompt)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"ok": True, "message": "Task created", "task": new_task, "tasksFile": src}),
        }

    if "[Run Report]" in normalized:
        embedded = _extract_embedded_json(prompt)
        payload = embedded if isinstance(embedded, dict) else data
        report_event = {
            "reportType": payload.get("reportType"),
            "input": payload.get("input", {}),
            "output": payload.get("output", {}),
            "params": payload.get("params", {}),
            "taskId": payload.get("taskId", "ui-report")
        }
        result = execute_report(report_event)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"ok": True, "report": result}),
        }

    result = call_bedrock(prompt)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(result),
    }


if __name__ == "__main__":
    class DevHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)
            event = {"body": body.decode("utf-8")}
            resp = lambda_handler(event, None)
            self.send_response(resp["statusCode"])
            for h, v in resp.get("headers", {}).items():
                self.send_header(h, v)
            self.end_headers()
            self.wfile.write(resp["body"].encode("utf-8"))

    def _mask(val: str) -> str:
        if not val:
            return '<empty>'
        s = str(val)
        if len(s) <= 8:
            return '****'
        return f"{s[:4]}...{s[-4:]}"

    def _log_effective_config():
        try:
            keys = {
                'AWS_ACCESS_KEY_ID': _cfg('AWS_ACCESS_KEY_ID'),
                'AWS_SECRET_ACCESS_KEY': _cfg('AWS_SECRET_ACCESS_KEY'),
                'AWS_SESSION_TOKEN': _cfg('AWS_SESSION_TOKEN'),
                'AWS_BEARER_TOKEN_BEDROCK': _cfg('AWS_BEARER_TOKEN_BEDROCK'),
                'AWS_REGION': _cfg('AWS_REGION'),
                'BEDROCK_MODEL_ID': _cfg('BEDROCK_MODEL_ID'),
                'BEDROCK_MOCK': _cfg('BEDROCK_MOCK') or _cfg('USE_MOCK_BEDROCK')
            }
            logger.info('Effective configuration (values masked):')
            for k, v in keys.items():
                logger.info('  %s = %s', k, _mask(v))
        except Exception as e:
            logger.warning('Failed to log effective config: %s', e)

    _log_effective_config()

    print("Starting local dev server at http://0.0.0.0:8000 (POST /)")
    HTTPServer(("0.0.0.0", 8000), DevHandler).serve_forever()