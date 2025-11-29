from typing import Dict, Any

REPORT_TYPE = "sample-summary"

# Simple sample: summarize numeric columns and count records

def process(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # ctx: { input: {source, path/uri, format}, params: {...} }
    data = ctx.get("data") or []
    # compute a tiny summary
    count = len(data) if isinstance(data, list) else 0
    metrics = {"records": count}
    return {"ok": True, "data": {"summary": f"Processed {count} records"}, "metrics": metrics}
