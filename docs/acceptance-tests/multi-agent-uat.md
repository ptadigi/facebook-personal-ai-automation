---
last_updated: 2026-03-05
compatible_scripts: v2.1.x
skill: facebook-personal-ai-automation
---

# Multi-Agent UAT (User Acceptance Tests)
**Version:** 2.1.0 · **Compatible scripts:** v2.1.x · **Last updated:** 2026-03-05
**Scope:** Clawbot + Claude Code + Antigravity — all agents, contract parity verification

---

## How to Run

```bash
# Prerequisites
python scripts/account_manager.py test --id <test_account>  # must be ACTIVE
# Live tests: need valid cookies + Facebook session
# Offline tests: pytest tests/ -v (no credentials needed)
```

Each test has: **Setup**, **Action**, **Expected**, **Pass criteria**, **Fail criteria**.

---

## Section 1 — Output Contract Parity Tests

### UAT-CONTRACT-001: Published post returns OK: published
```
Setup:     Account with valid session exists
Action:    python scripts/post.py --account <id> --text "UAT test" --auto-approve
Expected:  stdout last line: OK: published | url: https://...
Pass:      Last line starts with "OK: published | url: https://"
Fail:      Any deviation, no url field, or different structure
Agent:     Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-002: Scheduled post returns OK: scheduled
```
Setup:     Account with valid session
Action:    post.py --account <id> --text "Test" --schedule "2026-12-31T23:00:00+07:00"
Expected:  OK: scheduled 2026-12-31T23:00:00+07:00
Pass:      Exact format "OK: scheduled <ISO8601>"
Fail:      Different format, missing datetime, or no output
Agent:     Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-003: Dry run returns WAIT_APPROVAL
```
Setup:     Any valid account
Action:    post.py --account <id> --text "test" --dry-run
Expected:  WAIT_APPROVAL
Pass:      stdout last line is exactly "WAIT_APPROVAL"
Fail:      Post actually published, or different output
Agent:     Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-004: Invalid account returns FAIL or rejection
```
Setup:     No account with id "nonexistent_12345"
Action:    post.py --account nonexistent_12345 --text "test"
Expected:  FAIL: or agent-level rejection before command runs
Pass:      "FAIL: <code>" from script OR agent rejects with clear message
Fail:      Script crashes unstructured, or agent runs without validation
Agent:     Clawbot ✅  Claude Code ✅  Antigravity ✅
```

---

## Section 2 — Clawbot-Specific UAT

### UAT-CLAW-001: Vietnamese trigger — đăng bài
```
Setup:     Account "pham_thanh" active
Input:     "đăng bài Hôm nay đẹp trời bằng account pham_thanh"
Expected:
  1. Identifies intent=post, account=pham_thanh, text="Hôm nay đẹp trời"
  2. Asks user confirmation (or auto-approves)
  3. Runs post.py with correct args
  4. Returns success message with URL
Pass:      Post published, URL returned, no crash
Fail:      Wrong account, wrong text, no confirmation, crash
```

### UAT-CLAW-002: English trigger — schedule post
```
Input:     "schedule 'Good morning Vietnam!' for tomorrow 8am using account pham_thanh"
Expected:
  1. Resolves datetime to next day 08:00 +07:00
  2. Validates datetime is in the future ✅
  3. Runs post.py --schedule "YYYY-MM-DDTHH:00:00+07:00"
  4. Returns "OK: scheduled ..."
Pass:      Correct datetime resolved, schedule accepted
Fail:      Time wrong, no timezone, past datetime accepted
```

### UAT-CLAW-003: Input validation — missing media file
```
Input:     "đăng ảnh /tmp/nonexistent_photo.jpg lên fb"
Expected:
  - Path("/tmp/nonexistent_photo.jpg").exists() → False
  - REJECT before running any command
  - User message: "❌ Không tìm thấy file: /tmp/nonexistent_photo.jpg"
Pass:      Command NOT run, user informed
Fail:      Command runs and fails internally
```

### UAT-CLAW-004: AUTH_REQUIRED error handling
```
Setup:     Account with expired cookies
Action:    Clawbot runs post → gets "FAIL: AUTH_REQUIRED"
Expected:
  1. Marks account as expired (no auto-retry)
  2. Shows step-by-step cookie refresh instructions
  3. Does NOT retry automatically
Pass:      Instructions shown, no auto-retry
Fail:      Retried with same cookies, or no message
```

### UAT-CLAW-005: DOM_CHANGED auto-fix
```
Setup:     Inject DOM_CHANGED (clear selector-map.json)
Action:    Clawbot runs post → gets "FAIL: DOM_CHANGED"
Expected:
  1. Auto-runs dom_learner.py
  2. If dom_learner succeeds → retries post
  3. User notified of auto-fix
Pass:      dom_learner runs, retry attempted, user informed
Fail:      No auto-fix, user left hanging
```

### UAT-CLAW-006: RATE_LIMIT auto-queue
```
Setup:     Account returns RATE_LIMIT
Action:    Clawbot runs post → gets "FAIL: RATE_LIMIT"
Expected:
  1. Queues retry via scheduler.py --add (+45 min)
  2. Notifies user: "Đã đặt lịch retry lúc HH:MM"
  3. Does NOT immediately retry
Pass:      scheduler.py --add called with future time, user notified
Fail:      Immediate retry, or no queue, or no message
```

---

## Section 3 — Claude Code-Specific UAT

### UAT-CLAUDE-001: Tool schema validation
```
Setup:     Claude has read skills/claude-skill.md
Input:     Post request without required 'account' field
Expected:  Claude raises validation error before calling bash
Pass:      No command executed, error reported
Fail:      Command runs with missing required arg
```

### UAT-CLAUDE-002: Output parsing — published
```
stdout = "OK: published | url: https://facebook.com/posts/123 | account: pham_thanh"
Action:    parse_output(stdout)
Expected:  {"status": "published", "url": "https://...", "account": "pham_thanh"}
Pass:      All fields correct
Fail:      Wrong status, URL not extracted
```

### UAT-CLAUDE-003: Output parsing — all FAIL codes
```
FAIL: AUTH_REQUIRED - Session expired   → error_code="AUTH_REQUIRED"
FAIL: DOM_CHANGED - All selectors       → error_code="DOM_CHANGED"
FAIL: RATE_LIMIT - Facebook throttle    → error_code="RATE_LIMIT"
FAIL: PUBLISH_FAILED - Retry exhausted  → error_code="PUBLISH_FAILED"

Pass:      All 4 codes correctly parsed
Fail:      Any code returns wrong string or None
```

### UAT-CLAUDE-004: validate_schedule — timezone required
```
Input:     schedule = "2026-03-06T10:00:00"  (no timezone)
Expected:  ValueError raised before command runs
Pass:      Exception with timezone requirement message
Fail:      Command runs with naive datetime
```

### UAT-CLAUDE-005: Multi-media command building
```
Input:     media = ["img1.jpg", "img2.jpg", "img3.jpg"]
Expected:  cmd contains ["--media","img1.jpg","--media","img2.jpg","--media","img3.jpg"]
Pass:      Exact flags built correctly
Fail:      Only first media, space-separated, or wrong format
```

---

## Section 4 — Antigravity-Specific UAT

### UAT-AG-001: SKILL.md loading
```
Setup:     SKILL.md in repo root
Action:    Antigravity reads SKILL.md
Expected:  Correctly identifies available actions and output contract
Pass:      Agent knows 6 actions (post/story/reel/account.*/proxy.*)
Fail:      Agent hallucinates commands
```

### UAT-AG-002: run_command working directory
```
Action:    Antigravity runs any post command
Expected:  Working directory is repo root (SKILL_ROOT)
Pass:      scripts/post.py resolves correctly
Fail:      FileNotFoundError or wrong path
```

### UAT-AG-003: parse_output for all 4 states
```
"OK: published | url: https://... | account: X" → status=published
"OK: scheduled 2026-03-06T10:00:00+07:00"       → status=scheduled
"WAIT_APPROVAL"                                   → status=wait_approval
"FAIL: AUTH_REQUIRED - reason"                   → status=failed, error_code=AUTH_REQUIRED

Pass:      All 4 correctly parsed
Fail:      Any misparse or KeyError
```

### UAT-AG-004: Auto DOM heal workflow
```
Setup:     post.py returns FAIL: DOM_CHANGED
Expected:
  1. dom_learner.py runs with --account and --cookie-file
  2. If exit 0: retry post
  3. Report includes "selectors auto-updated"
Pass:      Full auto-heal cycle without user intervention
Fail:      dom_learner not triggered, or no outcome reported
```

### UAT-AG-005: validate_account rejects unknown id
```
Input:     account_id = "ghost_account_xyz"
Action:    validate_account("ghost_account_xyz")
Expected:  ValueError: "Account 'ghost_account_xyz' not registered"
Pass:      Exception raised, command NOT run
Fail:      Command runs, or wrong error
```

---

## Section 5 — Regression / Anti-Breakage Tests

### UAT-REGR-001: post.py flags unchanged
```
Action:    python scripts/post.py --help
Expected:  --account, --text, --media, --schedule, --dry-run, --auto-approve all present
Pass:      All flags exist
Fail:      Any flag removed or renamed
```

### UAT-REGR-002: account_manager.py commands unchanged
```
Commands:  init, add, list, test, assign, remove
Pass:      All 6 subcommands recognized
Fail:      Any subcommand removed or args changed
```

### UAT-REGR-003: scheduler.py queue format unchanged
```
Expected fields in queue entries: id, status, scheduled_at, text, media,
                                   cookie_file, content_hash, created_at, result
Pass:      All fields present in new entries
Fail:      Field removed or renamed
```

### UAT-REGR-004: 48 unit tests pass
```
Action:    pytest tests/ -v
Expected:  48 passed, 0 failed, 0 errors
Pass:      All 48 green
Fail:      Any failure
```

### UAT-REGR-005: selector-map.json format
```
Action:    python -m json.tool references/selector-map.json
Expected:  Valid JSON with "selectors" key containing "open_composer"
Pass:      Valid JSON, required key present
Fail:      Invalid JSON, key missing
```

---

## Regression Guard — Output Contract

### TC-REG-001: Output contract stability (all agents)

- **Goal:** Ensure future changes do not break parser compatibility across all agents.
- **Steps:**
  1. Run feed post, schedule post, dry-run, and one forced error path (invalid account).
  2. Capture the final non-empty stdout line for each scenario.
  3. Verify each line matches exactly one of the accepted patterns:
     - `OK: published | url: <URL> | account: <id>`
     - `OK: scheduled <ISO8601>`
     - `WAIT_APPROVAL`
     - `FAIL: <ERROR_CODE> - <reason>`
- **Pass criteria:** 100% of outputs match contract exactly — no extra prefix, suffix, or format drift.
- **Fail criteria:** Any output format deviation that breaks an existing parser (Clawbot, Claude, or Antigravity).
- **Run after:** Every code change to `post.py`, `scheduler.py`, `test_story.py`, or `test_reel.py`.

---

## Pass/Fail Summary Table

| Test ID | Description | Agent | Type | Expected |
|---|---|---|---|---|
| CONTRACT-001 | Published output format | All | Contract | `OK: published \| url:` |
| CONTRACT-002 | Scheduled output format | All | Contract | `OK: scheduled ISO8601` |
| CONTRACT-003 | Dry run output | All | Contract | `WAIT_APPROVAL` |
| CONTRACT-004 | Invalid account | All | Validation | Reject cleanly |
| CLAW-001 | VN trigger đăng bài | Clawbot | E2E | Post published |
| CLAW-002 | EN trigger schedule | Clawbot | E2E | Scheduled OK |
| CLAW-003 | Missing media file | Clawbot | Validation | Rejected before command |
| CLAW-004 | AUTH_REQUIRED handling | Clawbot | Error | Instructions shown, no retry |
| CLAW-005 | DOM_CHANGED auto-fix | Clawbot | Error | dom_learner run + retry |
| CLAW-006 | RATE_LIMIT auto-queue | Clawbot | Error | Queued +45min |
| CLAUDE-001 | Schema validation | Claude | Validation | No command without required |
| CLAUDE-002 | Parse published output | Claude | Unit | Dict correct |
| CLAUDE-003 | Parse all FAIL codes | Claude | Unit | All 4 correct |
| CLAUDE-004 | Schedule timezone | Claude | Validation | ValueError on no-tz |
| CLAUDE-005 | Multi-media cmd build | Claude | Unit | Correct --media flags |
| AG-001 | SKILL.md loading | Antigravity | E2E | Contract known |
| AG-002 | Working directory | Antigravity | E2E | No path errors |
| AG-003 | parse_output all states | Antigravity | Unit | 4/4 correct |
| AG-004 | DOM auto-heal | Antigravity | Error | Full cycle |
| AG-005 | Validate unknown account | Antigravity | Validation | ValueError |
| REGR-001 | post.py flags present | All | Regression | All flags exist |
| REGR-002 | account_manager commands | All | Regression | 6 subcommands |
| REGR-003 | Queue schema stable | All | Regression | All fields present |
| REGR-004 | 48 unit tests pass | All | Regression | 48/48 green |
| REGR-005 | selector-map format | All | Regression | Valid JSON |
| TC-REG-001 | Output contract stability | All | Regression | 100% format match |

**Minimum acceptance:** All REGR + CONTRACT + TC-REG tests must pass before any release.
