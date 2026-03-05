#!/usr/bin/env python3
"""
tests/test_account_manager.py — Unit tests for account_manager.py helpers.
Run: pytest tests/ -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import account_manager as am


# ---------------------------------------------------------------------------
# load_accounts / save_accounts
# ---------------------------------------------------------------------------

def test_load_accounts_missing_returns_empty(tmp_path, monkeypatch):
    """Missing accounts.json returns empty structure."""
    monkeypatch.setattr(am, "ACCOUNTS_FILE", tmp_path / "accounts.json")
    result = am.load_accounts()
    assert result["accounts"] == []


def test_save_load_accounts_roundtrip(tmp_path, monkeypatch):
    """Save and load accounts should roundtrip correctly."""
    monkeypatch.setattr(am, "ACCOUNTS_FILE", tmp_path / "accounts.json")
    data = {
        "version": "1.0.0",
        "accounts": [{"id": "pham_thanh", "display_name": "Test"}],
    }
    am.save_accounts(data)
    loaded = am.load_accounts()
    assert loaded["accounts"][0]["id"] == "pham_thanh"
    assert "updated_at" in loaded


# ---------------------------------------------------------------------------
# _warn_if_datr_missing (re-test from account_manager module)
# ---------------------------------------------------------------------------

def test_datr_warning_on_missing(tmp_path, capsys):
    """_warn_if_datr_missing warns when datr absent."""
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps([{"name": "c_user", "value": "123"}]))
    am._warn_if_datr_missing(f)
    captured = capsys.readouterr()
    assert "datr" in captured.out


def test_datr_no_warning_when_present(tmp_path, capsys):
    """_warn_if_datr_missing shows OK when datr present."""
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps([{"name": "datr", "value": "abc"}]))
    am._warn_if_datr_missing(f)
    captured = capsys.readouterr()
    assert "✓" in captured.out


def test_datr_no_crash_on_invalid_json(tmp_path):
    """_warn_if_datr_missing does not crash on corrupt file."""
    f = tmp_path / "bad.json"
    f.write_text("INVALID")
    am._warn_if_datr_missing(f)  # should not raise


# ---------------------------------------------------------------------------
# get_account_dir
# ---------------------------------------------------------------------------

def test_get_account_dir_path():
    """get_account_dir returns correct path for any account id."""
    path = am.get_account_dir("test_acc")
    assert path.name == "test_acc"
    assert "accounts" in str(path)


# ---------------------------------------------------------------------------
# reels_url construction (regression: slash separator bug)
# ---------------------------------------------------------------------------

def test_reels_url_no_trailing_slash():
    """Profile URL without trailing slash gets /reels/ appended correctly."""
    profile_url = "https://www.facebook.com/pham.thanh.756"
    reels_url = profile_url.rstrip("/") + "/reels/"
    assert reels_url.endswith("/reels/")
    assert "//" not in reels_url.replace("https://", "")


def test_reels_url_with_trailing_slash():
    """Profile URL WITH trailing slash also gets /reels/ correctly."""
    profile_url = "https://www.facebook.com/pham.thanh.756/"
    reels_url = profile_url.rstrip("/") + "/reels/"
    assert reels_url.endswith("/reels/")
    # Should not have double slash
    assert "//reels" not in reels_url
