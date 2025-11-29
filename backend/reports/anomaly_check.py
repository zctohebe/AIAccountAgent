from typing import Dict, Any

REPORT_TYPE = "anomaly-check"

# Very naive anomaly check: flag records with negative amount

def process(ctx: Dict[str, Any]) -> Dict[str, Any]:
    data = ctx.get("data") or []
    anomalies = []
    for i, row in enumerate(data):
        amt = None
        if isinstance(row, dict):
            amt = row.get("amount")
        if isinstance(amt, (int, float)) and amt < 0:
            anomalies.append({"index": i, "row": row})
    return {"ok": True, "data": {"anomalies": anomalies}, "metrics": {"count": len(anomalies)}}
