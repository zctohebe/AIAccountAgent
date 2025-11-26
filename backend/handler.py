import os
import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def call_bedrock(prompt: str):
    """Invoke Bedrock model. This function uses a best-effort boto3 client name and returns a safe mock on error.
    Replace the invocation details with the exact Bedrock SDK call for your environment.
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "<YOUR_MODEL_ID>")
    try:
        client = boto3.client("bedrock-runtime")
    except Exception:
        try:
            client = boto3.client("bedrock")
        except Exception:
            client = None

    payload = {"input": prompt}

    if client is None:
        logger.warning("No Bedrock client available; returning mock response")
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        # NOTE: Replace this call with the correct Bedrock runtime invocation for your SDK version.
        resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(payload))

        # Response shapes differ; try to extract text safely.
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
        logger.exception("Bedrock invocation failed")
        return {"ok": False, "error": str(e), "model_response": f"(mock) echo: {prompt}"}


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
    result = call_bedrock(prompt)

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
            event = {"body": body.decode("utf-8")}
            resp = lambda_handler(event, None)
            self.send_response(resp["statusCode"])
            # Copy headers from lambda response (includes CORS)
            for h, v in resp.get("headers", {}).items():
                self.send_header(h, v)
            self.end_headers()
            self.wfile.write(resp["body"].encode("utf-8"))

    print("Starting local dev server at http://0.0.0.0:8000 (POST /)")
    HTTPServer(("0.0.0.0", 8000), DevHandler).serve_forever()
