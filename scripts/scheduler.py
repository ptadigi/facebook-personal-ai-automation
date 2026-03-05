#!/usr/bin/env python3
"""
scheduler.py — Schedule queue daemon for facebook-personal-browser-post.

Reads references/schedule-queue.json for pending posts, fires post.py
at the scheduled time, and updates the queue status.

Schedule queue format (schedule-queue.json):
  [
    {
      "id": "unique-id",
      "status": "pending",         // pending | done | failed | cancelled
      "scheduled_at": "2026-03-06T10:00:00+07:00",
      "text": "Hello!",
      "media": [],
      "link": null,
      "cookie_file": "cookies.json",
      "created_at": "2026-03-05T08:41:00+07:00",
      "result": null               // filled after execution
    }
  ]

Usage:
  # Run daemon (checks every 60s)
  python scripts/scheduler.py --cookie-file cookies.json

  # Add a post to the queue
  python scripts/scheduler.py --add \
    --text "Hello!" \
    --schedule "2026-03-06T10:00:00+07:00" \
    --cookie-file cookies.json

  # List pending posts
  python scripts/scheduler.py --list

  # Cancel a pending post
  python scripts/scheduler.py --cancel <id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = SKILL_ROOT / "references" / "schedule-queue.json"
DEFAULT_RUN_LOG = SKILL_ROOT / "references" / "run-log.jsonl"
POST_SCRIPT = Path(__file__).resolve().parent / "post.py"

CHECK_INTERVAL = 60   # seconds between queue checks
# Fix 6: configurable post timeout (env override: POST_TIMEOUT_SECONDS)
POST_TIMEOUT = int(os.environ.get("POST_TIMEOUT_SECONDS", "300"))
# Fix 7: minimum minutes between posts per account (env override: MIN_POST_GAP_MINUTES)
MIN_POST_GAP_MINUTES = int(os.environ.get("MIN_POST_GAP_MINUTES", "15"))


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_dt(iso: str) -> datetime:
    """Parse an ISO 8601 datetime string to a timezone-aware datetime."""
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        # Assume local timezone
        dt = dt.astimezone()
    return dt


# ---------------------------------------------------------------------------
# Queue I/O
# ---------------------------------------------------------------------------

def load_queue(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_queue(path: Path, queue: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_event(run_log_path: Path, phase: str, status: str, note: str):
    record = {
        "timestamp": _now_iso(),
        "phase": phase,
        "status": status,
        "note": note,
        "error_code": None,
    }
    try:
        run_log_path.parent.mkdir(parents=True, exist_ok=True)
        with run_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Execute a queued post
# ---------------------------------------------------------------------------

def execute_post(entry: dict, run_log: Path) -> str:
    """
    Run post.py for a queued entry. Returns the result line (e.g. 'OK: published').
    """
    cmd = [sys.executable, str(POST_SCRIPT), "--auto-approve"]
    cmd += ["--cookie-file", entry.get("cookie_file", "cookies.json")]

    if entry.get("text"):
        cmd += ["--text", entry["text"]]

    for m in entry.get("media", []):
        cmd += ["--media", m]

    if entry.get("link"):
        cmd += ["--link", entry["link"]]

    log_event(run_log, "scheduler", "ok", f"Firing post for queue id={entry['id']}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            # Fix 6: use configurable timeout (default 300s) to support large video uploads
            timeout=POST_TIMEOUT,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stderr:
            # Fix 10: strip post text content from stderr before logging (PII protection)
            sanitized_stderr = re.sub(r'--text [\'"].{0,200}[\'"]', '--text [REDACTED]', stderr)
            sanitized_stderr = sanitized_stderr[:300]
            log_event(run_log, "scheduler", "warn", f"post.py stderr: {sanitized_stderr}")

        # Last non-empty line is the status
        lines = [l for l in stdout.splitlines() if l.strip()]
        status_line = lines[-1] if lines else "FAIL: PUBLISH_FAILED - No output from post.py"
        log_event(run_log, "scheduler", "ok", f"post.py result: {status_line}")
        return status_line

    except subprocess.TimeoutExpired:
        msg = f"FAIL: PUBLISH_FAILED - post.py timed out after {POST_TIMEOUT}s"
        log_event(run_log, "scheduler", "fail", msg)
        return msg
    except Exception as exc:
        msg = f"FAIL: PUBLISH_FAILED - {exc}"
        log_event(run_log, "scheduler", "fail", msg)
        return msg


def _last_fire_time(queue: list[dict], account_id: str, current_id: str) -> datetime | None:
    """
    Fix 7 helper: find the most recent executed_at time for any post in this account,
    excluding the current entry. Used to enforce minimum inter-post delay.
    """
    last = None
    for e in queue:
        if e["id"] == current_id:
            continue
        if e.get("status") != "done":
            continue
        acc = e.get("account") or e.get("cookie_file", "")
        if acc != account_id:
            continue
        executed_at = e.get("executed_at")
        if not executed_at:
            continue
        try:
            dt = datetime.fromisoformat(executed_at)
            if dt.tzinfo is None:
                dt = dt.astimezone(timezone.utc)
            if last is None or dt > last:
                last = dt
        except Exception:
            pass
    return last


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

def run_daemon(queue_path: Path, run_log: Path):
    print(f"[scheduler] Daemon started. Queue: {queue_path}")
    print(f"[scheduler] Check interval: {CHECK_INTERVAL}s. Press Ctrl+C to stop.\n")
    log_event(run_log, "scheduler", "ok", "Daemon started")

    while True:
        queue = load_queue(queue_path)
        now = _now()
        changed = False

        for entry in queue:
            if entry.get("status") != "pending":
                continue

            try:
                sched_dt = parse_dt(entry["scheduled_at"])
            except Exception as exc:
                entry["status"] = "failed"
                entry["result"] = f"FAIL: invalid scheduled_at — {exc}"
                changed = True
                continue

            if sched_dt <= now:
                # Fix 7: enforce minimum inter-post delay per account
                account_id = entry.get("account") or entry.get("cookie_file", "unknown")
                last_fire = _last_fire_time(queue, account_id, entry["id"])
                if last_fire and (now - last_fire) < timedelta(minutes=MIN_POST_GAP_MINUTES):
                    wait_min = MIN_POST_GAP_MINUTES - int((now - last_fire).total_seconds() / 60)
                    log_event(run_log, "scheduler", "warn",
                              f"Skipping post id={entry['id']} — inter-post gap not met. Retry in ~{wait_min}min.")
                    continue

                print(f"[scheduler] Firing post id={entry['id']} scheduled for {entry['scheduled_at']}")
                result = execute_post(entry, run_log)
                entry["result"] = result
                entry["executed_at"] = _now_iso()
                entry["status"] = "done" if result.startswith("OK:") else "failed"
                changed = True
                print(f"[scheduler] Result: {result}")

        if changed:
            save_queue(queue_path, queue)

        time.sleep(CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_add(args, queue_path: Path):
    """Add a post to the schedule queue."""
    if not args.schedule:
        print("[ERROR] --schedule is required with --add")
        sys.exit(1)

    # Validate datetime
    try:
        parse_dt(args.schedule)
    except Exception as exc:
        print(f"[ERROR] Invalid --schedule datetime: {exc}")
        sys.exit(1)

    queue = load_queue(queue_path)

    # Fix 8: content hash deduplication — block re-queuing same content at same time
    content_hash = hashlib.md5(
        f"{args.text or ''}{','.join(args.media or [])}{args.schedule}".encode()
    ).hexdigest()[:12]
    duplicate = next(
        (e for e in queue if e.get("content_hash") == content_hash and e["status"] == "pending"),
        None
    )
    if duplicate:
        print(f"[scheduler] ⚠  Duplicate detected — same content already queued as id={duplicate['id']} at {duplicate['scheduled_at']}")
        print("[scheduler] Use --cancel <id> first if you want to replace it.")
        sys.exit(0)

    entry = {
        "id": str(uuid.uuid4())[:8],
        "status": "pending",
        "scheduled_at": args.schedule,
        "text": args.text or "",
        "media": args.media or [],
        "link": args.link or None,
        "cookie_file": args.cookie_file,
        "content_hash": content_hash,
        "created_at": _now_iso(),
        "result": None,
    }
    queue.append(entry)
    save_queue(queue_path, queue)
    print(f"[scheduler] Queued post id={entry['id']} for {args.schedule} (hash={content_hash})")
    print(f"  Text: {entry['text'][:80]}")
    print(f"  Media: {entry['media']}")


def cmd_list(queue_path: Path):
    """List all queued posts."""
    queue = load_queue(queue_path)
    if not queue:
        print("[scheduler] Queue is empty.")
        return
    print(f"{'ID':<10} {'STATUS':<12} {'SCHEDULED AT':<30} {'TEXT'}")
    print("-" * 80)
    for e in queue:
        text_preview = (e.get("text") or "")[:40]
        print(f"{e['id']:<10} {e['status']:<12} {e.get('scheduled_at',''):<30} {text_preview}")


def cmd_cancel(entry_id: str, queue_path: Path):
    """Cancel a pending post."""
    queue = load_queue(queue_path)
    found = False
    for e in queue:
        if e["id"] == entry_id and e["status"] == "pending":
            e["status"] = "cancelled"
            found = True
            break
    if found:
        save_queue(queue_path, queue)
        print(f"[scheduler] Cancelled post id={entry_id}")
    else:
        print(f"[scheduler] No pending post with id={entry_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Schedule daemon for facebook-personal-browser-post")
    p.add_argument("--cookie-file", default="cookies.json", help="Default cookie file for queued posts")
    p.add_argument("--queue", default=str(DEFAULT_QUEUE), help="Path to schedule-queue.json")
    p.add_argument("--run-log", default=str(DEFAULT_RUN_LOG), help="Path to run-log.jsonl")

    # Sub-commands
    p.add_argument("--add", action="store_true", help="Add a post to the queue")
    p.add_argument("--list", action="store_true", help="List queued posts")
    p.add_argument("--cancel", metavar="ID", help="Cancel a pending post by ID")

    # Post fields (used with --add)
    p.add_argument("--text", default="", help="Post text")
    p.add_argument("--media", action="append", default=[], metavar="PATH", help="Media file")
    p.add_argument("--link", default=None, help="Link URL")
    p.add_argument("--schedule", default=None, metavar="ISO8601", help="Scheduled datetime")

    return p.parse_args()


def main():
    args = parse_args()
    queue_path = Path(args.queue)
    run_log = Path(args.run_log)

    if args.list:
        cmd_list(queue_path)
    elif args.cancel:
        cmd_cancel(args.cancel, queue_path)
    elif args.add:
        cmd_add(args, queue_path)
    else:
        run_daemon(queue_path, run_log)


if __name__ == "__main__":
    main()
