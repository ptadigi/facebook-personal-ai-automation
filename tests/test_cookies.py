#!/usr/bin/env python3
"""
tests/test_cookies.py — Unit tests for scripts/lib/cookies.py
Run: pytest tests/ -v  (no Facebook cookies required)
"""
import json
import os
import sys
from pathlib import Path

import pytest

# Make scripts importable without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.cookies import (
    harden_file,
    inject_cookies,
    load_cookies,
    warn_if_datr_missing,
)


# ---------------------------------------------------------------------------
# load_cookies
# ---------------------------------------------------------------------------

def test_load_cookies_flat_list(tmp_path):
    """Flat JSON list is accepted directly."""
    data = [{"name": "c_user", "value": "123", "domain": ".facebook.com", "path": "/"}]
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps(data))
    result = load_cookies(f)
    assert isinstance(result, list)
    assert result[0]["name"] == "c_user"


def test_load_cookies_wrapped_dict(tmp_path):
    """{'cookies': [...]} wrapper format is unwrapped correctly."""
    data = {"cookies": [{"name": "xs", "value": "abc"}]}
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps(data))
    result = load_cookies(f)
    assert result[0]["name"] == "xs"


def test_load_cookies_missing_file():
    """FileNotFoundError raised for nonexistent file."""
    with pytest.raises(FileNotFoundError):
        load_cookies("/tmp/does_not_exist_abc123.json")


def test_load_cookies_invalid_json(tmp_path):
    """Corrupt JSON raises an exception."""
    f = tmp_path / "bad.json"
    f.write_text("{ this is not json }")
    with pytest.raises(Exception):
        load_cookies(f)


def test_load_cookies_unrecognised_format(tmp_path):
    """A plain dict without 'cookies' key raises ValueError."""
    f = tmp_path / "weird.json"
    f.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(ValueError, match="Unrecognised"):
        load_cookies(f)


# ---------------------------------------------------------------------------
# warn_if_datr_missing
# ---------------------------------------------------------------------------

def test_warn_if_datr_missing_warns(capsys):
    """Warning printed when datr cookie absent."""
    cookies = [{"name": "c_user", "value": "123"}]
    warn_if_datr_missing(cookies, label="test")
    captured = capsys.readouterr()
    assert "datr" in captured.err
    assert "WARNING" in captured.err


def test_warn_if_datr_present_no_warning(capsys):
    """No warning when datr is present."""
    cookies = [{"name": "datr", "value": "abc123"}, {"name": "c_user", "value": "999"}]
    warn_if_datr_missing(cookies, label="test")
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err
    assert "✓" in captured.out


# ---------------------------------------------------------------------------
# inject_cookies (tests Playwright context mock)
# ---------------------------------------------------------------------------

class MockContext:
    def __init__(self):
        self.added = []

    def add_cookies(self, cookies):
        self.added.extend(cookies)


def test_inject_cookies_sameSite_normalisation():
    """Invalid sameSite values are normalised to 'None'."""
    ctx = MockContext()
    inject_cookies(ctx, [{"name": "x", "value": "y", "sameSite": "INVALID"}])
    assert ctx.added[0]["sameSite"] == "None"


def test_inject_cookies_valid_sameSite_preserved():
    """Valid sameSite values Strict/Lax/None are preserved."""
    ctx = MockContext()
    inject_cookies(ctx, [
        {"name": "a", "value": "1", "sameSite": "Strict"},
        {"name": "b", "value": "2", "sameSite": "Lax"},
        {"name": "c", "value": "3", "sameSite": "None"},
    ])
    assert ctx.added[0]["sameSite"] == "Strict"
    assert ctx.added[1]["sameSite"] == "Lax"
    assert ctx.added[2]["sameSite"] == "None"


def test_inject_cookies_expirationDate_mapped():
    """Cookie-Editor 'expirationDate' is mapped to Playwright 'expires' int."""
    ctx = MockContext()
    inject_cookies(ctx, [{"name": "x", "value": "y", "expirationDate": 1999999999.5}])
    assert ctx.added[0]["expires"] == 1999999999


def test_inject_cookies_default_domain():
    """Missing domain defaults to .facebook.com."""
    ctx = MockContext()
    inject_cookies(ctx, [{"name": "x", "value": "y"}])
    assert ctx.added[0]["domain"] == ".facebook.com"


# ---------------------------------------------------------------------------
# harden_file (best-effort on this OS)
# ---------------------------------------------------------------------------

def test_harden_file_no_crash(tmp_path):
    """harden_file should never raise — silently skips on Windows."""
    f = tmp_path / "test.json"
    f.write_text("{}")
    harden_file(f)  # should not raise
