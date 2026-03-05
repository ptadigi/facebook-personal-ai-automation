# Multi-Agent UAT (User Acceptance Tests)
**Skill:** `facebook-personal-ai-automation` · **Version:** 2.1.0  
**Scope:** Clawbot + Claude Code + Antigravity — all agents, contract parity verification

---

## How to Run

```bash
# Prerequisites
python scripts/account_manager.py test --id <test_account>  # must be ACTIVE
# For live tests: need valid cookies + Facebook session
# For offline tests: pytest tests/ -v (no credentials needed)
```

Each test has:
- **Setup** — prestate required
- **Action** — exact command or agent input
- **Expected** — exact expected output pattern
- **Pass criteria** — what constitutes PASS
- **Fail criteria** — what constitutes FAIL

---

## Section 1 — Output Contract Parity Tests

These verify all 3 agents produce the same output format.

### UAT-CONTRACT-001: Published post returns OK: published
```
Setup:     Account with valid session exists
Action:    python scripts/post.py --account <id> --text "UAT test" --auto-approve
Expected:  stdout last line matches: ^OK: published \| url: https://
Pass:      stdout last line starts with "OK: published | url: https://"
Fail:      Any deviation from this format, or no url field, or different structure
Agent coverage: Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-002: Scheduled post returns OK: scheduled
```
Setup:     Account with valid session
Action:    post.py --account <id> --text "Scheduled" --schedule "2026-12-31T23:00:00+07:00"
Expected:  OK: scheduled 2026-12-31T23:00:00+07:00
Pass:      Exact format "OK: scheduled <ISO8601>"
Fail:      Different format, missing datetime, or no output
Agent coverage: Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-003: Dry run returns WAIT_APPROVAL
```
Setup:     Any valid account
Action:    post.py --account <id> --text "test" --dry-run
Expected:  WAIT_APPROVAL
Pass:      stdout last line is exactly "WAIT_APPROVAL"
Fail:      Post is actually published, or different output
Agent coverage: Clawbot ✅  Claude Code ✅  Antigravity ✅
```

### UAT-CONTRACT-004: Invalid account returns FAIL:
```
Setup:     No account with id "nonexistent_12345"
Action:    post.py --account nonexistent_12345 --text "test"
Expected:  FAIL: or agent-level validation rejection before command runs
Pass:      Either "FAIL: <code>" from script OR agent rejects input with clear message
Fail:      Script crashes without structured output, or agent runs without validation
Agent coverage: Clawbot ✅  Claude Code ✅  Antigravity ✅
```

---

## Section 2 — Clawbot-Specific UAT

### UAT-CLAW-001: Vietnamese trigger — đăng bài
```
Setup:     Account "pham_thanh" active, no media
Input:     "đăng bài Hôm nay đẹp trời bằng account pham_thanh"
Expected:
  1. Clawbot identifies intent=post, account=pham_thanh, text="Hôm nay đẹp trời"
  2. Asks user confirmation (or auto-approves if configured)
  3. Runs post.py with correct args
  4. Returns success message with URL
Pass:      Post published, URL returned to user, no crash
Fail:      Wrong account used, wrong text, no confirmation step, crash
```

### UAT-CLAW-002: English trigger — schedule post
```
Input:     "schedule 'Good morning Vietnam!' for tomorrow 8am using account pham_thanh"
Expected:
  1. Clawbot resolves datetime to next day 08:00 +07:00
  2. Validates datetime is in the future ✅
  3. Runs post.py --schedule "YYYY-MM-DDTHH:00:00+07:00"
  4. Returns "OK: scheduled ..."
Pass:      Correct datetime resolved, schedule accepted
Fail:      Time resolved to wrong day/hour, no timezone, past datetime
```

### UAT-CLAW-003: Input validation — missing media file
```
Input:     "đăng ảnh /tmp/nonexistent_photo.jpg lên fb"
Expected:
  - Clawbot checks: Path("/tmp/nonexistent_photo.jpg").exists() → False
  - REJECT before running command
  - User message: "❌ Không tìm thấy file: /tmp/nonexistent_photo.jpg"
Pass:      Command NOT run, user informed of missing file
Fail:      Command runs and fails internally, or no clear message to user
```

### UAT-CLAW-004: AUTH_REQUIRED error handling
```
Setup:     Account with expired cookies
Action:    Clawbot runs post → gets "FAIL: AUTH_REQUIRED"
Expected:
  1. Clawbot marks account as expired (no auto-retry)
  2. Shows step-by-step cookie refresh instructions
  3. Does NOT retry automatically
Pass:      Fix instructions shown, no auto-retry attempted
Fail:      Retried with same (expired) cookies, or no user message
```

### UAT-CLAW-005: DOM_CHANGED auto-fix
```
Setup:     Simulate DOM_CHANGED (can inject by clearing selector-map.json)
Action:    Clawbot runs post → gets "FAIL: DOM_CHANGED"
Expected:
  1. Clawbot auto-runs dom_learner.py
  2. If dom_learner succeeds → retries post
  3. User notified of auto-fix
Pass:      dom_learner runs, retry attempted, user informed
Fail:      No auto-fix, or user left hanging without explanation
```

### UAT-CLAW-006: RATE_LIMIT auto-queue
```
Setup:     Account that returns RATE_LIMIT
Action:    Clawbot runs post → gets "FAIL: RATE_LIMIT"
Expected:
  1. Clawbot queues retry via scheduler.py --add (+45 min)
  2. Notifies user: "Đã đặt lịch retry lúc HH:MM"
  3. Does NOT immediately retry
Pass:      scheduler.py --add called with future time, user notified
Fail:      Immediate retry attempted, or no queue created, or no user message
```

---

## Section 3 — Claude Code-Specific UAT

### UAT-CLAUDE-001: Tool schema validation
```
Setup:     Claude has read skills/claude-skill.md
Input:     Post request without required 'account' field
Expected:  Claude raises input validation error before calling bash
Pass:      No command executed, error reported to user
Fail:      Command runs with missing required arg, or crash
```

### UAT-CLAUDE-002: Output parsing — published
```
Setup:     Mock stdout = "OK: published | url: https://facebook.com/posts/123 | account: pham_thanh"
Action:    parse_output(stdout) called
Expected:  {"status": "published", "url": "https://facebook.com/posts/123", "account": "pham_thanh"}
Pass:      Correct dict returned with all fields
Fail:      Wrong status, URL not extracted, dict missing keys
```

### UAT-CLAUDE-003: Output parsing — all FAIL codes
```
For each error code:
  FAIL: AUTH_REQUIRED - Session expired        → error_code="AUTH_REQUIRED"
  FAIL: DOM_CHANGED - All selectors failed     → error_code="DOM_CHANGED"
  FAIL: RATE_LIMIT - Facebook throttle         → error_code="RATE_LIMIT"
  FAIL: PUBLISH_FAILED - Retry exhausted       → error_code="PUBLISH_FAILED"

Pass:      All 4 codes correctly parsed
Fail:      Any code returns wrong string or None
```

### UAT-CLAUDE-004: validate_schedule — timezone required
```
Input:     schedule = "2026-03-06T10:00:00"  (no timezone)
Expected:  ValueError raised before command runs
Pass:      Exception raised with message explaining timezone requirement
Fail:      Command runs with naive datetime, or wrong error type
```

### UAT-CLAUDE-005: Multi-media command building
```
Input:     media = ["img1.jpg", "img2.jpg", "img3.jpg"]
Expected:  cmd contains: ["--media", "img1.jpg", "--media", "img2.jpg", "--media", "img3.jpg"]
Pass:      Exact flags built correctly
Fail:      Only first media, or space-separated, or different format
```

---

## Section 4 — Antigravity-Specific UAT

### UAT-AG-001: SKILL.md loading
```
Setup:     SKILL.md in repo root
Action:    Antigravity reads SKILL.md
Expected:  Can describe available actions, output contract, and CLI args
Pass:      Agent correctly identifies 6 actions (post/story/reel/account.*/proxy.*)
Fail:      Agent doesn't know the contract, hallucinates commands
```

### UAT-AG-002: run_command working directory
```
Action:    Antigravity runs any post command
Expected:  Working directory is repo root (SKILL_ROOT)
Pass:      Command resolves scripts/post.py correctly, accounts/ found
Fail:      FileNotFoundError, wrong path, or relative path fails
```

### UAT-AG-003: parse_output for all 4 states
```
Test each:
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
Action:    Antigravity triggers dom_learner.py automatically
Expected:
  1. dom_learner.py runs with --account and --cookie-file
  2. If exit 0: retry post
  3. Report includes "selectors auto-updated" note
Pass:      Full auto-heal cycle completes without user intervention
Fail:      dom_learner not triggered, or retry not attempted, or no outcome reported
```

### UAT-AG-005: validate_account rejects unknown id
```
Input:     account_id = "ghost_account_xyz"
Action:    validate_account("ghost_account_xyz") called
Expected:  ValueError: "Account 'ghost_account_xyz' not registered"
Pass:      Exception raised, command NOT run
Fail:      Command runs, or wrong error message
```

---

## Section 5 — Regression / Anti-Breakage Tests

Run these after ANY code change to verify backward compatibility.

### UAT-REGR-001: post.py output contract unchanged
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
Action:    Add a test entry to schedule-queue.json
Expected:  id, status, scheduled_at, text, media, cookie_file, content_hash, created_at, result fields present
Pass:      All fields present in new entries
Fail:      Field removed or renamed (breaks existing queues)
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
Action:    cat references/selector-map.json | python -m json.tool
Expected:  Valid JSON with "selectors" key containing "open_composer" at minimum
Pass:      Valid JSON, required key present
Fail:      Invalid JSON, key missing
```

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

**Minimum acceptance:** All REGR tests + CONTRACT tests must pass before any release.
