import os
import json
from pathlib import Path
from typing import Dict, Any, List

from backend.report_registry import ReportRegistry

try:
    import boto3
except Exception:
    boto3 = None

# Minimal loader for local files (JSON lines) and optional S3

def _read_jsonl_file(p: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rows.append(obj)
            except Exception:
                pass
    return rows


def _read_json_file(p: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        try:
            obj = json.load(f)
            if isinstance(obj, list):
                rows = obj
        except Exception:
            pass
    return rows


def _parse_s3_uri(uri: str) -> Dict[str, str]:
    # s3://bucket/key
    if not uri.startswith("s3://"):
        return {}
    rest = uri[len("s3://"):]
    parts = rest.split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    return {"bucket": bucket, "key": key}


def _s3_get_jsonl(bucket: str, key: str) -> List[Dict[str, Any]]:
    if not boto3:
        return []
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read().decode("utf-8", errors="replace")
    rows: List[Dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def _s3_get_json(bucket: str, key: str) -> List[Dict[str, Any]]:
    if not boto3:
        return []
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read().decode("utf-8", errors="replace")
    try:
        obj = json.loads(body)
        return obj if isinstance(obj, list) else []
    except Exception:
        return []


def _s3_put_json(bucket: str, key: str, obj: Dict[str, Any]) -> str:
    if not boto3:
        return ""
    s3 = boto3.client("s3")
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="application/json; charset=utf-8")
    return f"s3://{bucket}/{key}"


def load_input(input_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = input_spec.get("source", "local")
    fmt = input_spec.get("format", "jsonl")
    path = input_spec.get("path") or input_spec.get("uri")
    if not path:
        return []

    if source == "s3":
        s3_parts = _parse_s3_uri(path)
        bucket, key = s3_parts.get("bucket"), s3_parts.get("key")
        if not bucket or not key:
            return []
        if fmt == "jsonl":
            return _s3_get_jsonl(bucket, key)
        elif fmt == "json":
            return _s3_get_json(bucket, key)
        else:
            return []

    # default local
    p = Path(path)
    if not p.exists():
        return []
    if fmt == "jsonl":
        return _read_jsonl_file(p)
    elif fmt == "json":
        return _read_json_file(p)
    else:
        return []


def persist_output(output_spec: Dict[str, Any], task_id: str, result: Dict[str, Any]) -> str:
    target = output_spec.get("target", "local")
    path = output_spec.get("path")
    if target == "s3":
        uri = path or output_spec.get("uri")
        parts = _parse_s3_uri(uri or "")
        bucket, key = parts.get("bucket"), parts.get("key")
        if not bucket or not key:
            return ""
        return _s3_put_json(bucket, key, result)

    # default local
    if not path:
        path = f"results/{task_id}-report.json"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return str(p)


def execute(event: Dict[str, Any]) -> Dict[str, Any]:
    # event: {reportType, input: {...}, output: {...}, params: {...}, taskId}
    report_type = event.get("reportType")
    task_id = event.get("taskId", "report-task")
    registry = ReportRegistry()
    registry.discover()
    handler = registry.get(report_type)
    if not handler:
        return {"ok": False, "error": f"Unknown reportType: {report_type}"}
    data_rows = load_input(event.get("input", {}))
    ctx = {"data": data_rows, "params": event.get("params", {})}
    result = handler(ctx)
    out_path = persist_output(event.get("output", {}), task_id, result)
    return {"ok": True, "outputPath": out_path, "result": result, "reportType": report_type}
