# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 2.1.x | ✅ Active support |
| 2.0.x | ⚠️ Security fixes only |
| < 2.0 | ❌ No support |

---

## 🔐 Known Security Considerations

This tool interacts with Facebook using your personal session cookies. Please review these important points:

1. **Cookie files** are stored in `accounts/<id>/cookies.json` with `0o600` permissions (owner-only read/write). **Never commit these files to Git.**

2. **Proxy credentials** are stored in `proxies/proxy-list.json` in plaintext (gitignored). Future versions will encrypt these via OS keyring.

3. **`schedule-queue.json`** may contain absolute paths to cookie files. It should be added to `.gitignore` (see [docs/security-audit.md](docs/security-audit.md) A1).

4. **Log files** (`references/run-log.jsonl`) do not contain post content or cookie values, but do contain account IDs and post URLs.

5. **No remote telemetry** — this tool makes no outbound connections except to Facebook.com via Playwright.

---

## 🚨 Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in this project, please report it responsibly:

### How to Report

**Email:** Create a private GitHub Security Advisory by clicking:
[Report a vulnerability](https://github.com/ptadigi/facebook-personal-ai-automation/security/advisories/new)

Or email the maintainer directly (see GitHub profile for contact info).

### What to Include

1. **Description** of the vulnerability
2. **Steps to reproduce** (exact command or scenario)
3. **Potential impact** (what could an attacker do?)
4. **Affected versions** (which version(s) are vulnerable?)
5. **Suggested fix** (optional, but appreciated)

### Response Timeline

| Stage | Timeline |
|---|---|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix release | Within 30 days (critical), 90 days (others) |
| Public disclosure | After fix is released |

---

## 🛡️ Security Best Practices for Users

```bash
# 1. Keep cookies protected
chmod 600 accounts/*/cookies.json
chmod 600 accounts/*/fingerprint.json
chmod 700 accounts/

# 2. Never commit sensitive files
cat .gitignore | grep -E "cookies|proxy|queue"

# 3. Rotate cookies regularly (Facebook sessions expire)
python scripts/account_manager.py test --id <id>

# 4. Use proxies to reduce account fingerprint correlation
python scripts/proxy_manager.py add --host <proxy> --port <port> --country VN
```

---

## ⚠️ Platform Policy Disclaimer

This tool automates Facebook interaction which may violate [Facebook's Terms of Service](https://www.facebook.com/terms) and [Automated Data Collection Terms](https://www.facebook.com/apps/site_scraping_tos_terms.php).

Users are solely responsible for:
- Compliance with Facebook's Terms of Service
- Compliance with local laws and regulations
- Any consequences including account suspension or legal action

The maintainers of this project are not liable for any misuse.
