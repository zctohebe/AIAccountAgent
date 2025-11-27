import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Ensure repository root is on sys.path so 'backend' package is importable when running from scripts/
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import backend Bedrock caller and report executor
from backend.handler import call_bedrock
from backend.report_executor import execute as execute_report

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(_handler)

STATE_PATH = REPO_ROOT / "resources" / "scheduler_state.json"
NOTIFY_PATH = REPO_ROOT / "resources" / "notifications.json"


def repo_root() -> Path:
    return REPO_ROOT


def find_tasks_file() -> Path:
    """Find tasks.json in common locations: repo root, resources/tasks.json"""
    candidates = [repo_root() / "tasks.json", repo_root() / "resources" / "tasks.json"]
    for p in candidates:
        if p.exists():
            return p
    return candidates[1]


def _read_json_with_fallback(p: Path) -> Any:
    encodings = ["utf-8", "utf-8-sig", "cp936", "gbk", "latin-1"]
    last_err = None
    for enc in encodings:
        try:
            with p.open("r", encoding=enc) as f:
                return json.load(f)
        except Exception as e:
            last_err = e
    raise last_err


def load_tasks(tasks_path: Path) -> list:
    if not tasks_path.exists():
        return []
    try:
        tasks = _read_json_with_fallback(tasks_path)
    except Exception:
        logger.exception("Failed to read tasks.json with encoding fallbacks: %s", tasks_path)
        return []
    if not isinstance(tasks, list):
        logger.warning("tasks.json is not a JSON array: %s", tasks_path)
        return []
    return tasks


def ensure_parent_dir(file_path: Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)


def write_state(jobs: Dict[str, Dict[str, Any]]):
    try:
        ensure_parent_dir(STATE_PATH)
        with STATE_PATH.open("w", encoding="utf-8") as f:
            json.dump({"jobs": jobs, "updated": datetime.utcnow().isoformat() + "Z"}, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to write scheduler_state.json")


def append_notification(message: Dict[str, Any]):
    try:
        ensure_parent_dir(NOTIFY_PATH)
        existing = []
        if NOTIFY_PATH.exists():
            with NOTIFY_PATH.open("r", encoding="utf-8") as f:
                try:
                    existing = json.load(f) or []
                except Exception:
                    existing = []
        existing.append(message)
        with NOTIFY_PATH.open("w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to append notification")


def run_task(task: dict):
    task_id = task.get("taskId", "unknown")
    prompt = task.get("prompt")
    output_path = task.get("outputPath", f"results/{task_id}-output.txt")
    report_event = task.get("reportEvent")

    logger.info("Running task %s", task_id)

    if report_event and isinstance(report_event, dict):
        try:
            evt = dict(report_event)
            evt["taskId"] = task_id
            result = execute_report(evt)
        except Exception as e:
            logger.exception("Task %s report execution failed: %s", task_id, e)
            result = {"ok": False, "error": str(e)}
    else:
        # default to Bedrock prompt flow
        try:
            result = call_bedrock(prompt or "Hello from AI Accounting Agent")
        except Exception as e:
            logger.exception("Task %s failed to call bedrock: %s", task_id, e)
            result = {"ok": False, "error": str(e), "model_response": f"(mock) error: {e}"}

    # Persist output
    try:
        dest = (repo_root() / output_path).resolve()
        ensure_parent_dir(dest)
        timestamp = datetime.utcnow().isoformat() + "Z"
        line = {
            "timestamp": timestamp,
            "taskId": task_id,
            "ok": bool(result.get("ok")),
            "response": result,
        }
        with dest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        logger.info("Task %s wrote output to %s", task_id, dest)
    except Exception:
        logger.exception("Task %s failed to write output", task_id)

    append_notification({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "taskId": task_id,
        "message": f"Task {task_id} executed",
        "ok": bool(result.get("ok")),
        "outputPath": output_path,
    })


def schedule_tasks(scheduler: BlockingScheduler, tasks: list, jobs_index: Dict[str, Dict[str, Any]]):
    enabled = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if not task.get("enabled", False):
            continue
        cron_expr = task.get("cron")
        task_id = str(task.get("taskId"))
        if not cron_expr or not task_id:
            continue
        if task_id not in jobs_index:
            try:
                trigger = CronTrigger.from_crontab(cron_expr)
                scheduler.add_job(run_task, trigger, args=[task], id=task_id, replace_existing=True, max_instances=1)
                jobs_index[task_id] = {"cron": cron_expr, "enabled": True}
                logger.info("Scheduled new task %s with cron '%s' (UTC)", task_id, cron_expr)
                enabled += 1
            except Exception:
                logger.exception("Failed to schedule task %s with cron '%s'", task_id, cron_expr)
        else:
            if jobs_index[task_id].get("cron") != cron_expr:
                try:
                    scheduler.remove_job(task_id)
                except Exception:
                    pass
                try:
                    trigger = CronTrigger.from_crontab(cron_expr)
                    scheduler.add_job(run_task, trigger, args=[task], id=task_id, replace_existing=True, max_instances=1)
                    jobs_index[task_id] = {"cron": cron_expr, "enabled": True}
                    logger.info("Updated task %s to cron '%s'", task_id, cron_expr)
                except Exception:
                    logger.exception("Failed to update task %s", task_id)
    write_state(jobs_index)
    if enabled == 0:
        logger.info("No new tasks scheduled in this cycle")


def main():
    tasks_path = find_tasks_file()
    scheduler = BlockingScheduler(timezone="UTC")
    jobs_index: Dict[str, Dict[str, Any]] = {}

    tasks = load_tasks(tasks_path)
    schedule_tasks(scheduler, tasks, jobs_index)

    def reload_tasks():
        new_tasks = load_tasks(tasks_path)
        schedule_tasks(scheduler, new_tasks, jobs_index)

    scheduler.add_job(reload_tasks, "interval", seconds=30, id="__reload__", replace_existing=True)
    logger.info("Local scheduler started (timezone=UTC). Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
