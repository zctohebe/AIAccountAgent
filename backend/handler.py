import os
import sys
import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import quote
from datetime import datetime
import uuid

# 创建一个 Logger 对象
logger = logging.getLogger()
# 设置日志级别为 DEBUG，表示记录所有级别的日志（DEBUG、INFO、WARNING、ERROR、CRITICAL）
logger.setLevel(logging.DEBUG)
# 创建一个控制台输出的 Handler
console_handler = logging.StreamHandler()
# 创建日志格式器并添加到 Handler 上
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# 将 Handler 添加到 Logger
logger.addHandler(console_handler)

#model_id = "deepseek-chat:1.0" #deepseek-chat:1.0 ,deepseek.r1-v1:0
aws_access_key_id=''
aws_secret_access_key=''
region_name = 'us-east-1'

def call_bedrock(prompt: str):
    """Invoke Bedrock model. This function uses a best-effort boto3 client name and returns a safe mock on error.
    Replace the invocation details with the exact Bedrock SDK call for your environment.
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "deepseek-chat:1.0")
    try:
            client = boto3.client(service_name='bedrock-runtime',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
            logger.info("Created Bedrock runtime client")
    except Exception:
        try:
            client = boto3.client("bedrock")
            logger.info("Created Bedrock client")
        except Exception:
            client = None
            logger.info("Did not Created Bedrock client")

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


        #resp = client.invoke_model(modelId=model_id,body='{"input_data": "鐢熸垚涓�娈靛叧浜庢湭鏉ョ鎶�鐨勭煭鏂囥�?}')
        output = resp['body'].read().decode('utf-8')
        print("妯″瀷杈撳嚭锛?, output)
        body = None


    # Response shapes differ; try to extract text safely.

        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        # NOTE: Replace this call with the correct Bedrock runtime invocation for your SDK version.

        resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(payload))
        output = resp['body'].read().decode('utf-8')
        print("妯″瀷杈撳嚭锛?, output)
        body = None
        if isinstance(resp, dict):
            body = resp.get("body") or resp.get("Body") or resp
        else:
            body = resp

        try:
            if isinstance(body, (bytes, bytearray)):
                text = body.decode("utf-8")
            else:
        return {"ok": False, "error": str(e), "model_response": f"(mock) echo: {prompt}"}
                try:
                    parsed = json.loads(json.dumps(body))
                    # try common response shapes
    # Prefer explicit path-based routing if provided by API Gateway
    if path and path.endswith("/presign"):
        result = handle_presign_request(data)
    else:
        # Allow clients to request presign via action in payload
        if isinstance(data, dict) and data.get("action") == "presign":
            result = handle_presign_request(data)
        else:
            result = handle_chat_request(data)
                            text = json.dumps(parsed['output'])
                        elif parsed.get('content'):
                            text = json.dumps(parsed['content'])
                        else:
        return {"ok": False, "error": str(e), "model_response": f"(mock) echo: {prompt}"}
                    else:
                        text = str(parsed)
                except Exception:
    prompt = data.get("prompt", "Hello from AI Accounting Agent")
    result = call_bedrock(prompt)
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
    """AWS Lambda handler expected by SAM/API Gateway."""
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
    print("Starting local dev server at http://0.0.0.0:8000 (POST /chat , POST /presign)")
    HTTPServer(("0.0.0.0", 8000), DevHandler).serve_forever()
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(result),
    }


# Minimal local dev server so you can test without SAM
if __name__ == "__main__":
    class DevHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_POST(self):
    print("Starting local dev server at http://0.0.0.0:8000 (POST /)")
    HTTPServer(("0.0.0.0", 8000), DevHandler).serve_forever()
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