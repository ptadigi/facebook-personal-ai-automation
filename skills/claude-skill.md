# Facebook Personal Browser Post — Claude MCP Tool Definition

This file defines the tool interface for use with **Claude** via the Model Context Protocol (MCP)
or as a function in an Anthropic API conversation.

---

## Tool Definition (MCP JSON)

```json
{
  "name": "facebook_post",
  "description": "Post content to a Facebook personal profile using browser automation. Supports text, images, videos, stories, and reels. Requires an initialized account with valid session cookies. Returns a structured result with the post URL.",
  "input_schema": {
    "type": "object",
    "properties": {
      "account": {
        "type": "string",
        "description": "Account ID configured in accounts/accounts.json (e.g. 'pham_thanh'). Use this for multi-account mode."
      },
      "text": {
        "type": "string",
        "description": "Text content for the post."
      },
      "media": {
        "type": "array",
        "items": { "type": "string" },
        "description": "List of absolute file paths to images or videos to attach."
      },
      "post_type": {
        "type": "string",
        "enum": ["feed", "story", "reel"],
        "default": "feed",
        "description": "Type of Facebook post. 'feed' for wall posts, 'story' for 24h stories, 'reel' for reel videos."
      },
      "schedule": {
        "type": "string",
        "description": "ISO 8601 datetime to schedule the post (e.g. '2026-03-06T10:00:00+07:00'). Leave empty to post immediately."
      },
      "auto_approve": {
        "type": "boolean",
        "default": false,
        "description": "If true, publish immediately without waiting for user approval."
      },
      "dry_run": {
        "type": "boolean",
        "default": false,
        "description": "If true, compose the post but do not publish. Returns WAIT_APPROVAL."
      }
    },
    "required": ["account"]
  }
}
```

---

## How Claude Should Invoke This Tool

When the user asks to post something on Facebook, Claude should:

1. **Identify the account** — ask the user which account if not specified
2. **Confirm content** — show a preview before `auto_approve: true`
3. **Check media paths** — ensure files exist before calling
4. **Invoke the tool** using the shell command below
5. **Report the URL** from the output

### Shell Invocation

```bash
# Feed post (text + image)
python scripts/post.py \
  --account {account} \
  --text "{text}" \
  --media "{media[0]}" \
  --auto-approve

# Story
python scripts/test_story.py \
  --cookie-file accounts/{account}/cookies.json \
  --media "{media[0]}"

# Reel
python scripts/test_reel.py \
  --cookie-file accounts/{account}/cookies.json \
  --media "{media[0]}" \
  --caption "{text}"
```

### Expected Output

```
OK: published | url: https://www.facebook.com/<user>/posts/<id> | account: pham_thanh
WAIT_APPROVAL
FAIL: AUTH_REQUIRED - Session expired
FAIL: DOM_CHANGED - Run dom_learner.py
```

---

## Claude Prompt Guidelines

When this tool is available, Claude should:

- **Never post without confirmation** unless `auto_approve` was explicitly requested
- **Always report the URL** from the output to the user
- **Handle AUTH_REQUIRED** by telling user to re-export cookies and run:
  ```
  python scripts/account_manager.py init --id {account} --cookies cookies.json
  ```
- **Handle DOM_CHANGED** by telling user to run:
  ```
  python scripts/dom_learner.py --cookie-file accounts/{account}/cookies.json
  ```
- **Never store or log** cookie file contents

---

## Account Setup (tell user)

```bash
# 1. Export cookies from browser (Cookie-Editor extension → JSON)
# 2. Initialize account
python scripts/account_manager.py init --id myaccount --cookies cookies.json

# 3. Verify
python scripts/account_manager.py test --id myaccount

# 4. (Optional) Add proxy
python scripts/proxy_manager.py add --host 1.2.3.4 --port 3128 --country VN
python scripts/account_manager.py assign --id myaccount --proxy proxy_1_2_3_4_3128
```

---

## Error Handling Map

| Error | Claude Response |
|---|---|
| `AUTH_REQUIRED` | "Session expired. Please re-export cookies and run `account_manager.py init`." |
| `DOM_CHANGED` | "Facebook updated its UI. Please run `dom_learner.py` to re-learn selectors." |
| `RATE_LIMIT` | "Facebook is rate-limiting this account. Wait 30+ minutes and try again." |
| `PUBLISH_FAILED` | "Post button was clicked but confirmation was not detected. Check screenshots in skill root." |
