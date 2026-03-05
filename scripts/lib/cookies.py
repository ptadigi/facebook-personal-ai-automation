#!/usr/bin/env python3
"""
lib/cookies.py — Shared cookie utilities for facebook-personal-browser-post.

Centralises cookie loading, normalisation, and injection logic used by:
  post.py, dom_learner.py, test_story.py, test_reel.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

__version__ = "2.1.0"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_cookies(cookie_file: str | Path) -> list[dict]:
    """
    Load cookies from a JSON file.

    Accepts two formats:
      - Flat list:          [ {name, value, domain, ...}, ... ]
      - Wrapped dict:       { "cookies": [ ... ] }

    Raises:
      FileNotFoundError if the file does not exist.
      ValueError if the format is unrecognised.
    """
    path = Path(cookie_file)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cookies" in data:
        return data["cookies"]
    if isinstance(data, list):
        return data
    raise ValueError(
        "Unrecognised cookie format. Expected a JSON list or {'cookies': [...]} dict."
    )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def warn_if_datr_missing(cookies: list[dict], label: str = "") -> None:
    """
    Print a warning if the 'datr' cookie is absent.

    'datr' is Facebook's primary device-tracking cookie.  Missing it is a
    high-confidence bot-detection signal.
    """
    names = {c.get("name", "") for c in cookies}
    prefix = f"[{label}] " if label else ""
    if "datr" not in names:
        print(
            f"  ⚠  {prefix}WARNING: 'datr' cookie not found.\n"
            "     Facebook uses 'datr' as a device fingerprint; missing it raises bot-detection risk.\n"
            "     Fix: clear browser storage, visit facebook.com, re-export with Cookie-Editor.",
            file=sys.stderr,
        )
    else:
        print(f"  ✓ {prefix}'datr' cookie present ✅")


# ---------------------------------------------------------------------------
# Inject into Playwright context
# ---------------------------------------------------------------------------

def inject_cookies(context, cookies: list[dict]) -> None:
    """
    Add a list of cookies to a Playwright browser context.

    Normalises common Cookie-Editor export fields to Playwright's expected
    schema, handling sameSite, expirationDate / expires, and defaults.
    """
    pw_cookies = []
    for c in cookies:
        pw_c: dict = {
            "name":     c.get("name", ""),
            "value":    c.get("value", ""),
            "domain":   c.get("domain", ".facebook.com"),
            "path":     c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure":   c.get("secure", False),
        }
        # sameSite must be exactly one of Strict / Lax / None
        raw_ss = c.get("sameSite", "None")
        pw_c["sameSite"] = raw_ss if raw_ss in ("Strict", "Lax", "None") else "None"

        # Expiry: Cookie-Editor uses 'expirationDate'; Playwright uses 'expires'
        if c.get("expirationDate"):
            pw_c["expires"] = int(c["expirationDate"])
        elif c.get("expires"):
            pw_c["expires"] = int(c["expires"])

        pw_cookies.append(pw_c)

    context.add_cookies(pw_cookies)


# ---------------------------------------------------------------------------
# Convenience: load + inject in one call
# ---------------------------------------------------------------------------

def load_and_inject(context, cookie_file: str | Path, *, check_datr: bool = True) -> list[dict]:
    """
    Load cookies from *cookie_file*, optionally warn about missing 'datr',
    then inject them into *context*.

    Returns the raw cookie list so callers can inspect it if needed.
    """
    cookies = load_cookies(cookie_file)
    if check_datr:
        warn_if_datr_missing(cookies, label=str(cookie_file))
    inject_cookies(context, cookies)
    return cookies


# ---------------------------------------------------------------------------
# File-permission hardening (best-effort: POSIX only)
# ---------------------------------------------------------------------------

def harden_file(path: Path) -> None:
    """
    Set path permissions to 0o600 (owner read/write only).
    Silent no-op on Windows where POSIX chmod semantics don't apply.
    """
    try:
        os.chmod(path, 0o600)
    except (AttributeError, NotImplementedError, OSError):
        pass
