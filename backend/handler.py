import os
import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler, HTTPServer

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
    


    if client is None:
        logger.warning("No Bedrock client available; returning mock response")
        return {"ok": False, "model_response": f"(mock) echo: {prompt}"}

    try:
        # NOTE: Replace this call with the correct Bedrock runtime invocation for your SDK version.

        resp = client.invoke_model(modelId=model_id, contentType="application/json", body=json.dumps(payload))

        #resp = client.invoke_model(modelId=model_id,body='{"input_data": "生成一段关于未来科技的短文。"}')
        output = resp['body'].read().decode('utf-8')
        print("模型输出：", output)
        body = None


    # Response shapes differ; try to extract text safely.
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
