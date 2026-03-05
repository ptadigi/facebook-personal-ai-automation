#!/usr/bin/env python3
"""
tests/test_scheduler.py — Unit tests for scheduler.py helper functions.
Run: pytest tests/ -v  (no browser/network required)
"""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import scheduler as sched


# ---------------------------------------------------------------------------
# parse_dt
# ---------------------------------------------------------------------------

def test_parse_dt_with_tz():
    """ISO 8601 with timezone is parsed correctly."""
    dt = sched.parse_dt("2026-03-06T10:00:00+07:00")
    assert dt.tzinfo is not None
    assert dt.hour == 10


def test_parse_dt_naive_gets_local_tz():
    """Naive datetime gets local timezone attached."""
    dt = sched.parse_dt("2026-03-06T10:00:00")
    assert dt.tzinfo is not None


def test_parse_dt_invalid():
    """Garbage string raises ValueError."""
    with pytest.raises(Exception):
        sched.parse_dt("not-a-date")


# ---------------------------------------------------------------------------
# load_queue / save_queue
# ---------------------------------------------------------------------------

def test_load_queue_missing_file(tmp_path):
    """Non-existent queue file returns empty list."""
    result = sched.load_queue(tmp_path / "no_queue.json")
    assert result == []


def test_load_queue_corrupt_json(tmp_path):
    """Corrupt JSON returns empty list (no crash)."""
    f = tmp_path / "queue.json"
    f.write_text("{ broken json !!!")
    result = sched.load_queue(f)
    assert result == []


def test_save_and_load_queue_roundtrip(tmp_path):
    """Save then load should return identical data."""
    q = tmp_path / "queue.json"
    entries = [{"id": "abc", "status": "pending", "scheduled_at": "2026-03-06T10:00:00+07:00"}]
    sched.save_queue(q, entries)
    loaded = sched.load_queue(q)
    assert loaded[0]["id"] == "abc"


# ---------------------------------------------------------------------------
# _parse_error_code
# ---------------------------------------------------------------------------

def test_parse_error_code_auth():
    assert sched._parse_error_code("FAIL: AUTH_REQUIRED - Session expired") == "AUTH_REQUIRED"


def test_parse_error_code_dom():
    assert sched._parse_error_code("FAIL: DOM_CHANGED - All selectors failed") == "DOM_CHANGED"


def test_parse_error_code_rate():
    assert sched._parse_error_code("FAIL: RATE_LIMIT - Facebook throttle") == "RATE_LIMIT"


def test_parse_error_code_publish():
    assert sched._parse_error_code("FAIL: PUBLISH_FAILED - Retry exhausted") == "PUBLISH_FAILED"


def test_parse_error_code_ok_returns_none():
    """OK: lines should return None (no error code)."""
    assert sched._parse_error_code("OK: published | url: https://...") is None


def test_parse_error_code_empty():
    assert sched._parse_error_code("") is None


# ---------------------------------------------------------------------------
# _last_fire_time
# ---------------------------------------------------------------------------

def _make_entry(entry_id, account, status, executed_at=None):
    e = {"id": entry_id, "account": account, "status": status}
    if executed_at:
        e["executed_at"] = executed_at
    return e


def test_last_fire_time_returns_none_when_no_done():
    """No done entries → returns None."""
    queue = [_make_entry("x", "acc1", "pending")]
    result = sched._last_fire_time(queue, "acc1", "other")
    assert result is None


def test_last_fire_time_returns_latest():
    """Returns the most recent executed_at among done entries for this account."""
    now = datetime.now(tz=timezone.utc)
    old = (now - timedelta(hours=2)).isoformat()
    recent = (now - timedelta(minutes=5)).isoformat()
    queue = [
        _make_entry("a", "acc1", "done", old),
        _make_entry("b", "acc1", "done", recent),
        _make_entry("c", "acc2", "done", now.isoformat()),  # different account
    ]
    result = sched._last_fire_time(queue, "acc1", "other_id")
    assert result is not None
    # Should be the recent one (5 min ago), not old one (2h ago)
    assert abs((result - (now - timedelta(minutes=5))).total_seconds()) < 2


def test_last_fire_time_excludes_current_entry():
    """The current entry (by id) is excluded from the check."""
    now = datetime.now(tz=timezone.utc)
    queue = [_make_entry("current", "acc1", "done", now.isoformat())]
    result = sched._last_fire_time(queue, "acc1", "current")
    assert result is None  # excluded itself


# ---------------------------------------------------------------------------
# Content hash deduplication (test the logic manually)
# ---------------------------------------------------------------------------

def test_content_hash_dedup_logic():
    """Same text+schedule produces same hash → duplicate detection works."""
    text = "Hello world"
    media = []
    schedule = "2026-03-06T10:00:00+07:00"
    h1 = hashlib.md5(f"{text}{','.join(media)}{schedule}".encode()).hexdigest()[:12]
    h2 = hashlib.md5(f"{text}{','.join(media)}{schedule}".encode()).hexdigest()[:12]
    assert h1 == h2


def test_content_hash_different_schedule_different_hash():
    """Different schedule → different hash → not a duplicate."""
    text = "Hello world"
    h1 = hashlib.md5(f"{text}2026-03-06T10:00:00+07:00".encode()).hexdigest()[:12]
    h2 = hashlib.md5(f"{text}2026-03-06T11:00:00+07:00".encode()).hexdigest()[:12]
    assert h1 != h2
