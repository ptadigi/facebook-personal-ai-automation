#!/usr/bin/env python3
"""
tests/test_post.py — Unit tests for post.py helper functions.
Run: pytest tests/ -v
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import post


# ---------------------------------------------------------------------------
# _rotate_log_if_needed
# ---------------------------------------------------------------------------

def test_rotate_log_trims_old_lines(tmp_path):
    """Log with > max_lines entries is trimmed to max_lines most recent."""
    log = tmp_path / "run-log.jsonl"
    lines = [f'{{"n": {i}}}\n' for i in range(100)]
    log.write_text("".join(lines))
    post._rotate_log_if_needed(log, max_lines=50)
    result = log.read_text().splitlines()
    assert len(result) == 50
    assert '"n": 99' in result[-1]  # last line is most recent


def test_rotate_log_no_op_under_limit(tmp_path):
    """Log with <= max_lines is unchanged."""
    log = tmp_path / "run-log.jsonl"
    lines = [f'{{"n": {i}}}\n' for i in range(10)]
    log.write_text("".join(lines))
    post._rotate_log_if_needed(log, max_lines=50)
    assert len(log.read_text().splitlines()) == 10


def test_rotate_log_no_crash_missing_file(tmp_path):
    """Missing log file is silently ignored."""
    post._rotate_log_if_needed(tmp_path / "nonexistent.jsonl", max_lines=100)


# ---------------------------------------------------------------------------
# log_event — new schema with run_id / account_id / version
# ---------------------------------------------------------------------------

def test_log_event_schema(tmp_path):
    """log_event writes correct schema including run_id and account_id."""
    log = tmp_path / "run-log.jsonl"
    post.log_event(
        log, "publish", "ok", "Test note",
        run_id="abc12345", account_id="pham_thanh"
    )
    record = json.loads(log.read_text().strip())
    assert record["phase"] == "publish"
    assert record["status"] == "ok"
    assert record["run_id"] == "abc12345"
    assert record["account_id"] == "pham_thanh"
    assert record["version"] == post.__version__
    assert record["error_code"] is None
    assert "timestamp" in record


def test_log_event_with_error_code(tmp_path):
    """log_event stores error_code correctly."""
    log = tmp_path / "run-log.jsonl"
    post.log_event(log, "auth", "fail", "Expired", error_code="AUTH_REQUIRED")
    record = json.loads(log.read_text().strip())
    assert record["error_code"] == "AUTH_REQUIRED"


def test_log_event_with_url(tmp_path):
    """log_event stores URL field correctly."""
    log = tmp_path / "run-log.jsonl"
    post.log_event(log, "publish", "ok", "Published", url="https://facebook.com/posts/123")
    record = json.loads(log.read_text().strip())
    assert record["url"] == "https://facebook.com/posts/123"


def test_log_event_no_crash_on_unwritable(tmp_path):
    """log_event silently warns if log file is unwritable (no exception propagation)."""
    fake_path = tmp_path / "nodir" / "nope.jsonl"
    # Should not raise — create parent dir even if it doesn't exist
    post.log_event(fake_path, "test", "ok", "Note")  # should create dir automatically


# ---------------------------------------------------------------------------
# extract_post_url — polling loop
# ---------------------------------------------------------------------------

def _make_mock_page(hrefs=None, url="https://www.facebook.com/"):
    """Create a minimal mock Playwright page for extract_post_url testing."""
    page = MagicMock()
    page.url = url

    def query_selector_all(pattern):
        if hrefs is None:
            return []
        result = []
        for href in hrefs:
            el = MagicMock()
            el.get_attribute.return_value = href
            result.append(el)
        return result

    page.query_selector_all = query_selector_all
    return page


def test_extract_post_url_finds_posts_link():
    """Returns URL when /posts/ anchor found on page."""
    page = _make_mock_page(hrefs=["/pham.thanh/posts/123456789"])
    with patch("time.sleep"):  # speed up test
        url = post.extract_post_url(page)
    assert url == "https://www.facebook.com/pham.thanh/posts/123456789"


def test_extract_post_url_returns_none_when_no_links():
    """Returns None after polling timeout when no post links found."""
    page = _make_mock_page(hrefs=[])

    # Patch time.time to make the loop expire immediately
    call_count = [0]
    original = time.time

    def fast_time():
        call_count[0] += 1
        if call_count[0] > 3:
            return original() + 15  # expire deadline
        return original()

    with patch("time.time", side_effect=fast_time), patch("time.sleep"):
        url = post.extract_post_url(page)
    assert url is None


def test_extract_post_url_fallback_to_current_url():
    """Falls back to page.url if it's a post URL."""
    page = _make_mock_page(hrefs=[], url="https://www.facebook.com/user/posts/987")
    with patch("time.sleep"):
        url = post.extract_post_url(page)
    assert "posts" in url


# ---------------------------------------------------------------------------
# VERSION
# ---------------------------------------------------------------------------

def test_version_string():
    """__version__ should be a semantic version string."""
    parts = post.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
