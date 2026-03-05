# Multi-Agent Usage Guide
**Skill:** `facebook-personal-ai-automation` · **Version:** 2.1.0

Tài liu này giải thích khi nào dùng agent nào, cách orchestrate nhiều agent, và best practice cho multi-agent setup.

---

## Decision Matrix  Dùng Agent Nào?

| Tiêu chí | Clawbot | Claude Code | Antigravity |
|---|---|---|---|
| **User interaction** | Chat-driven (VN/EN triggers) | Code-assisted, command-level | Autonomous agent in terminal |
| **Khi nào dùng** | Users ng bài qua chat | Dev iều khin bằng script/code | Batch automation từ agent pipeline |
| **Ngôn ngữ trigger** | Tiếng Vit + Tiếng Anh tự nhiên | Shell commands + code | run_command() Python |
| **Validation** | Built-in pre-command check | Code-level validation | Validate function + SKILL.md |
| **DOM self-heal** | Tự ng gọi dom_learner | Manual hoặc tự gọi | Tự ng trong error handler |
| **Scheduling** | Queue qua scheduler.py | Direct CLI | Orchestrate scheduler daemon |
| **Output parsing** | Đọc last stdout line | Parse output contract | parse_output() helper |
| **Logging** | run-log.jsonl | run-log.jsonl | run-log.jsonl |
| **Phù hợp nhất vi** | Marketing team, non-dev users | Developers, CI integration | Autonomous pipeline, cron jobs |

---

## Khi Nào Dùng Agent Nào  Quick Guide

```
User nhắn "ng bài" trong app chat
   Clawbot

Dev cần gọi posting từ script Python/Bash
   Claude Code vi bash_tool

Cần chạy batch posting 10 accounts tự ng không có người can thip
   Antigravity vi scheduler daemon

Cần debug khi Facebook i UI
   Bất kỳ agent nào + dom_learner.py

Cần schedule bài hàng ngày theo lch c nh
   scheduler daemon + Antigravity hoặc cron
```

---

## Architecture Overview

```
                        
                                 User / Operator          
                        
                                                
                    Chat UI         CLI    Code   Agent Pipeline
                                                
                  
                  Clawbot          Claude     Antigravity 
                (chat intent        Code      (autonomous) 
                 resolution)      (bash)      (run_command)|
                  
                                                      
                       
                                       
                          
                             Output Contract        
                             OK: published | url:   
                             OK: scheduled          
                             WAIT_APPROVAL          
                             FAIL: <CODE> - reason  
                          
                                       
                    
                                                         
                   
               post.py       test_story.py    test_reel.py 
              scheduler                                    
                   
                    
         
                             
   accounts.json  proxies  selector-map.json
```

---

## Shared Output Contract (All Agents)

Mọi agent **BẮT BUC** phải parse dòng cui cùng của stdout:

```
OK: published | url: https://www.facebook.com/<user>/posts/<id> | account: <id>
OK: scheduled <ISO8601>
WAIT_APPROVAL
FAIL: AUTH_REQUIRED - <reason>
FAIL: DOM_CHANGED - <reason>
FAIL: RATE_LIMIT - <reason>
FAIL: PUBLISH_FAILED - <reason>
```

**Rule:** Không thay i contract này. Backward compatible vi mọi agent version.

---

## Multi-Agent Orchestration Patterns

### Pattern 1: Chat-to-Automation (Clawbot iều phi Antigravity)

```
Clawbot nhận intent từ user
   Validate input (account, media, schedule)
   Gọi subprocess: python scripts/post.py
   Parse output contract
   Handle errors (DOM_CHANGED: chạy dom_learner  retry)
   Return result to user
```

### Pattern 2: Batch Scheduling (Antigravity + Scheduler Daemon)

```python
# Antigravity orchestrates multiple accounts
accounts = ["acc_01", "acc_02", "acc_03"]
for account_id in accounts:
    run_command(["python", "scripts/scheduler.py", "--add",
                 "--account", account_id,
                 "--text", f"Bài tuần của {account_id}",
                 "--schedule", "2026-03-06T09:00:00+07:00"])

# Scheduler daemon fires them with 15-min gap per account
run_command(["python", "scripts/scheduler.py", "--daemon"])
```

### Pattern 3: Claude Code as Middleware

```python
# Claude reads SKILL.md, builds commands, handles errors
def post_with_retry(account, text, max_retries=2):
    for attempt in range(max_retries):
        result = bash(f"python scripts/post.py --account {account} "
                      f"--text '{text}' --auto-approve")
        parsed = parse_output(result.stdout)
        if parsed["status"] == "published":
            return parsed["url"]
        elif parsed["error_code"] == "DOM_CHANGED":
            bash(f"python scripts/dom_learner.py --account {account} "
                 f"--cookie-file accounts/{account}/cookies.json")
        elif parsed["error_code"] == "AUTH_REQUIRED":
            raise AuthExpiredError(f"Account {account} needs new cookies")
    raise MaxRetriesError("Post failed after all retries")
```

---

## Environment Variables (Shared across agents)

| Variable | Default | Description |
|---|---|---|
| `POST_TIMEOUT_SECONDS` | `300` | Max time for each post subprocess |
| `MIN_POST_GAP_MINUTES` | `15` | Min gap between posts per account |
| `SCHEDULER_MAX_WORKERS` | `3` | Concurrent posts in scheduler daemon |

Set globally for all agents:

```bash
export POST_TIMEOUT_SECONDS=300
export MIN_POST_GAP_MINUTES=15
export SCHEDULER_MAX_WORKERS=3
```

---

## Shared Error Handling Protocol

All agents follow the same error decision tree:

```
FAIL: AUTH_REQUIRED
   ALWAYS escalate to human (needs new cookies)
   NEVER auto-retry

FAIL: DOM_CHANGED
   TRY: run dom_learner.py
   IF dom_learner OK: retry once
   IF dom_learner fails OR second DOM_CHANGED: escalate

FAIL: RATE_LIMIT
   AUTO: queue retry +45 minutes via scheduler
   IF 3+ in same day for same account: escalate

FAIL: PUBLISH_FAILED
   WAIT: 10 seconds
   AUTO: retry once
   IF still fails: escalate with screenshot info
```

---

## Log Correlation (Multi-agent tracing)

Mi invocation của post.py tạo mt `run_id` 8 ký tự  correlate logs:

```bash
# Filter logs by account
grep '"account_id": "pham_thanh"' references/run-log.jsonl

# Filter by run_id (single invocation trace)
grep '"run_id": "a1b2c3d4"' references/run-log.jsonl

# Find all failures
grep '"status": "fail"' references/run-log.jsonl

# Today's posts
grep "$(date +%Y-%m-%d)" references/run-log.jsonl | grep '"phase": "publish"'
```

Log schema:
```json
{
  "timestamp": "2026-03-05T18:30:00+07:00",
  "version": "2.1.0",
  "run_id": "a1b2c3d4",
  "account_id": "pham_thanh",
  "phase": "publish",
  "status": "ok",
  "note": "Post published",
  "error_code": null,
  "url": "https://..."
}
```

---

## Operator Runbook (Multi-agent production setup)

```
SETUP:
[ ] Clone repo + pip install -r requirements.txt + playwright install chromium
[ ] Add accounts: account_manager.py init --id X --cookies Y  (repeat per account)
[ ] Test accounts: account_manager.py test --id X  (all must be ACTIVE)
[ ] Add proxies (optional): proxy_manager.py add --host ... --country VN
[ ] Assign proxies: account_manager.py assign --id X --proxy proxy_X
[ ] Verify selector-map.json: cat references/selector-map.json | python -m json.tool
[ ] Set ENV: POST_TIMEOUT_SECONDS=300 MIN_POST_GAP_MINUTES=15

DAILY CHECKS:
[ ] account_manager.py test --id X  per active account
[ ] proxy_manager.py health
[ ] tail -20 references/run-log.jsonl | python -m json.tool
[ ] Check for RATE_LIMIT patterns (>3 per account per day)

WHEN FB DOES UI UPDATE:
[ ] FAIL: DOM_CHANGED received
[ ] Run: dom_learner.py --account X --cookie-file accounts/X/cookies.json
[ ] Verify: selector-map.json updated (check "updated_at" timestamp)
[ ] Re-test: post.py --account X --text "test" --dry-run
```



## Known Limitations
- Video posts may return 'URL not captured' even when publish succeeds; verify on profile feed.
- Reel permalink can lag 1-5 minutes after publish while Facebook processes media.
- RATE_LIMIT events may require cooldown and scheduled retry.
- DOM changes can temporarily break selectors until dom_learner/manual update is applied.

