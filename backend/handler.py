import os
import json
import logging
import boto3
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _log_credential_status():
    """Log whether AWS credentials and key environment settings are available (do not print secrets)."""
    try:
        env_ak = bool(os.environ.get('AWS_ACCESS_KEY_ID'))
        env_sk = bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))
        env_token = bool(os.environ.get('AWS_SESSION_TOKEN'))
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'unset'
        upload_bucket = os.environ.get('UPLOAD_BUCKET') or os.environ.get('S3_BUCKET') or 'unset'
        bedrock_model = os.environ.get('BEDROCK_MODEL_ID') or 'unset'
        use_mock = os.environ.get('USE_MOCK_BEDROCK', 'false')

        # Check if boto3 can locate any credentials via its session (this will not reveal secret values)
        sess = boto3.session.Session()
        creds = sess.get_credentials()
        creds_present = creds is not None and creds.access_key is not None

        if env_ak or env_sk:
            source = 'environment'
        elif creds_present:
            source = 'boto3-credential-chain (shared/instance-role/STS)'
        else:
            source = 'none'

        logger.info("AWS credential status: present=%s, source=%s, region=%s, upload_bucket=%s, bedrock_model=%s, use_mock=%s",
                    str(creds_present), source, region, upload_bucket, bedrock_model, use_mock)
    except Exception:
        logger.exception('Failed to determine AWS credential status')


# Log credential status once at startup
_log_credential_status()


def call_bedrock(prompt: str):
    """Invoke Bedrock model. This function uses a best-effort boto3 client name and returns a safe mock on error.
    It will try to adapt the payload shape for chat-style models that expect a `messages` field.
    Replace the invocation details with the exact Bedrock runtime invocation for your SDK version if needed.
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "<YOUR_MODEL_ID>")
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or None

    client = None
    try:
        if region:
            client = boto3.client("bedrock-runtime", region_name=region)
        else:
            client = boto3.client("bedrock-runtime")
    except Exception:
        try:
            if region:
                client = boto3.client("bedrock", region_name=region)
            else:
                client = boto3.client("bedrock")
        except Exception:
            client = None

    # Prepare a default payload; older examples used {"input": prompt}
    payload = {"input": prompt}

    # If model id looks like a chat model, build a `messages` structure many Bedrock chat models expect
    lower_id = (model_id or "").lower()
    if any(k in lower_id for k in ("claude", "chat", "nova", "converse")):
        # Use content array where each item is an object with a 'text' field (avoid 'type')
        messages_payload = [
            {"role": "user", "content": [{"text": prompt}]}
        ]
        payload = {"messages": messages_payload}

    if client is None:
        logger.warning("No Bedrock client available; returning mock response")
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        # Try invoking with the prepared payload
        resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(payload))

        # Response shapes differ; try to extract text safely.
        body = None
        if isinstance(resp, dict):
            body = resp.get("body") or resp.get("Body") or resp
        else:
            body = resp

        try:
            # Handle botocore StreamingBody
            if hasattr(body, 'read'):
                try:
                    raw = body.read()
                    if isinstance(raw, (bytes, bytearray)):
                        text = raw.decode('utf-8')
                        # try to parse JSON text
                        try:
                            parsed = json.loads(text)
                            text = json.dumps(parsed)
                        except Exception:
                            pass
                    else:
                        text = str(raw)
                except Exception:
                    text = str(body)
            elif isinstance(body, (bytes, bytearray)):
                text = body.decode("utf-8")
            else:
                # sometimes the service returns nested JSON; try to extract common fields
                try:
                    parsed = json.loads(json.dumps(body))
                    # try common response shapes
                    if isinstance(parsed, dict):
                        if parsed.get('output'):
                            text = json.dumps(parsed['output'])
                        elif parsed.get('content'):
                            text = json.dumps(parsed['content'])
                        else:
                            text = json.dumps(parsed)
                    else:
                        text = str(parsed)
                except Exception:
                    text = str(body)
        except Exception:
            text = str(body)

        return {"ok": True, "model_response": text}
    except Exception as e:
        # If validation error indicates messages missing or wrong shape, retry with alternate messages wrapper
        err_str = str(e)
        logger.exception("Bedrock invocation failed")
        try:
            if 'messages' in err_str or 'required key' in err_str or 'extraneous key' in err_str:
                logger.info('Retrying Bedrock invoke with alternate messages payload (content as strings)')
                # Some models expect content array of plain strings instead of objects
                retry_payload = {"messages": [{"role": "user", "content": [prompt]}]}
                resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(retry_payload))
                body = resp.get("body") if isinstance(resp, dict) else resp
                # handle StreamingBody if present
                if hasattr(body, 'read'):
                    try:
                        raw = body.read()
                        if isinstance(raw, (bytes, bytearray)):
                            text = raw.decode('utf-8')
                            try:
                                parsed = json.loads(text)
                                text = json.dumps(parsed)
                            except Exception:
                                pass
                        else:
                            text = str(raw)
                    except Exception:
                        text = str(body)
                elif isinstance(body, (bytes, bytearray)):
                    text = body.decode('utf-8')
                else:
                    try:
                        text = json.dumps(body)
                    except Exception:
                        text = str(body)
                return {"ok": True, "model_response": text}
        except Exception:
            logger.exception('Retry with alternate messages payload failed')

        return {"ok": False, "error": err_str, "model_response": f"(mock) echo: {prompt}"}


def presign_upload(filename: str, content_type: str = "application/octet-stream"):
    """Generate an S3 presigned POST for browser direct upload.
    Requires UPLOAD_BUCKET or S3_BUCKET environment variable.
    Returns dict with url, fields, and object key on success.
    """
    bucket = os.environ.get("UPLOAD_BUCKET") or os.environ.get("S3_BUCKET")
    if not bucket:
        logger.warning("No upload bucket configured in UPLOAD_BUCKET or S3_BUCKET")
        # Return a mock presign for local development
        key = f"mock/{uuid.uuid4()}_{filename}"
        return {"ok": True, "presigned": {"url": f"https://example.com/upload/{key}", "fields": {}, "key": key}, "mock": True}

    key = f"{os.environ.get('UPLOAD_PREFIX','uploads/')}{uuid.uuid4()}_{os.path.basename(filename)}"
    try:
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or None
        if region:
            s3 = boto3.client("s3", region_name=region)
        else:
            s3 = boto3.client("s3")
        presigned = s3.generate_presigned_post(Bucket=bucket, Key=key, Fields={"Content-Type": content_type}, ExpiresIn=int(os.environ.get('PRESIGN_EXPIRES', '3600')))
        return {"ok": True, "presigned": {"url": presigned["url"], "fields": presigned["fields"], "key": key}}
    except Exception as e:
        logger.exception("Failed to generate presigned URL")
        return {"ok": False, "error": str(e)}


def handle_chat_request(data: dict):
    prompt = data.get("prompt", "Hello from AI Accounting Agent")
    return call_bedrock(prompt)


def handle_presign_request(data: dict):
    filename = data.get("filename") or data.get("name") or "upload.bin"
    content_type = data.get("content_type") or data.get("contentType") or "application/octet-stream"
    return presign_upload(filename, content_type)


def lambda_handler(event, context):
    """AWS Lambda handler expected by SAM/API Gateway.
    Supports two paths for local/dev: /chat and /presign (or action in body).
    """
    path = event.get("path") if isinstance(event, dict) else None
    body = event.get("body") if isinstance(event, dict) else None
    if isinstance(body, str):
        try:
            data = json.loads(body)
        except Exception:
            data = {"prompt": body}
    else:
        data = body or {}

    # Prefer explicit path-based routing if provided by API Gateway
    if path and path.endswith("/presign"):
        result = handle_presign_request(data)
    else:
        # Allow clients to request presign via action in payload
        if isinstance(data, dict) and data.get("action") == "presign":
            result = handle_presign_request(data)
        else:
            result = handle_chat_request(data)

    # Include CORS headers so local browser frontends can call the dev server
    return {
        "statusCode": 200,
        "headers": {
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
            # Handle CORS preflight
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)
            event = {"path": self.path, "body": body.decode("utf-8")}
            resp = lambda_handler(event, None)
            self.send_response(resp["statusCode"])
            # Copy headers from lambda response (includes CORS)
            for h, v in resp.get("headers", {}).items():
                self.send_header(h, v)
            self.end_headers()
            self.wfile.write(resp["body"].encode("utf-8"))

    print("Starting local dev server at http://0.0.0.0:8000 (POST /chat , POST /presign)")
    HTTPServer(("0.0.0.0", 8000), DevHandler).serve_forever()
