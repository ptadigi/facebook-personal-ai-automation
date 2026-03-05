# DOM Capture Playbook

How to discover and update selectors for the Facebook personal profile posting flow.
Run this playbook whenever Facebook updates its UI and selectors stop working (`DOM_CHANGED` error).

---

## When to Run

- After receiving `FAIL: DOM_CHANGED` from `post.py`
- After a Facebook UI refresh / redesign
- Proactively: once a month as preventive maintenance
- After a major Playwright update

---

## Automated Re-Capture

```bash
python scripts/dom_learner.py --cookie-file cookies.json [--headless]
```

This script:
1. Opens a Chromium browser with your session cookies
2. Navigates to `https://www.facebook.com`
3. Probes each action step in sequence, trying selectors in priority order
4. Writes updated selectors to `references/selector-map.json`
5. Appends any changed selectors to `references/selector-map.history.jsonl`
6. Prints a summary of what changed

---

## Manual Re-Capture (Fallback)

Use this if the automated script cannot find a selector.

### Step 1 — Open Facebook in a headed browser

```bash
# Launch with cookies loaded, keep browser open for inspection
python scripts/dom_learner.py --cookie-file cookies.json --interactive
```

Or manually open Chromium and import your cookie JSON.

### Step 2 — Inspect Each Action

For each action below, open DevTools (F12) → Elements tab, then follow the instructions.

---

### Action: `open_composer`

**What it is**: The "What's on your mind?" clickable area that opens the post composer dialog.

**Steps**:
1. On your Facebook home/profile page, find the text area at the top of the feed
2. Right-click → "Inspect"
3. Look for selectors in this priority:
   - `[aria-label]` or `role="button"` attributes
   - `data-testid` or other `data-*` attributes
   - Visible text content (e.g., "What's on your mind?")
   - XPath as last resort: `//div[@role='button'][contains(., "What")]`

**Record in selector-map.json under**: `"open_composer"`

---

### Action: `text_input`

**What it is**: The contenteditable area inside the composer where post text is typed.

**Steps**:
1. Click the composer to open it
2. Inspect the text area that appears
3. Priority selectors:
   - `[contenteditable="true"][role="textbox"]`
   - `[data-testid*="composer"]`
   - `[aria-label*="post"]` (case-insensitive)
   - XPath: `//div[@role='textbox' and @contenteditable='true']`

**Record under**: `"text_input"`

---

### Action: `media_button`

**What it is**: The photo/video attachment button in the composer toolbar.

**Steps**:
1. With composer open, look at the bottom toolbar
2. Find the camera/photo icon button
3. Priority selectors:
   - `[aria-label*="Photo"]` or `[aria-label*="Video"]`
   - `[data-testid*="photo"]`
   - Button with SVG icon — look for parent `role="button"`
   - XPath: `//div[@role='button'][.//*[local-name()='svg']][contains(@aria-label,'Photo')]`

**Record under**: `"media_button"`

---

### Action: `file_input`

**What it is**: The hidden `<input type="file">` element triggered after clicking media button.

**Steps**:
1. After clicking the media button, an `<input type="file">` appears in the DOM (may be hidden)
2. In DevTools, use Ctrl+F to search: `type="file"`
3. Priority selectors:
   - `input[type="file"][accept*="image"]`
   - `input[type="file"][accept*="video"]`
   - `input[type="file"]` (generic)
   - XPath: `//input[@type='file']`

**Record under**: `"file_input"`

---

### Action: `schedule_entry`

**What it is**: The button or menu item to access the scheduling options.

**Steps**:
1. In the composer, look for a clock icon or "..." more options button
2. Click it — find "Schedule post" or similar
3. Priority selectors:
   - `[aria-label*="Schedule"]` or `[aria-label*="schedule"]`
   - `[data-testid*="schedule"]`
   - Text: button containing "Schedule post"
   - XPath: `//div[@role='menuitem'][contains(.,'Schedule')]`

**Record under**: `"schedule_entry"`

---

### Action: `publish_button`

**What it is**: The final "Post" button that submits the post.

**Steps**:
1. With composer filled in, find the blue "Post" button
2. Priority selectors:
   - `[aria-label="Post"]` with `role="button"`
   - `[data-testid*="react-composer-post-button"]`
   - Text match: button with exact text "Post"
   - XPath: `//div[@role='button'][@aria-label='Post']`

**Record under**: `"publish_button"`

---

### Action: `schedule_confirm`

**What it is**: The confirm button in the scheduling dialog.

**Steps**:
1. Open scheduler UI → set a date/time
2. Find the confirm/save button
3. Priority selectors:
   - `[aria-label*="Schedule"]` inside the dialog
   - `[data-testid*="schedule-confirm"]`
   - Text: "Schedule" button inside a dialog `[role="dialog"]`
   - XPath: `//div[@role='dialog']//div[@role='button'][contains(.,'Schedule')]`

**Record under**: `"schedule_confirm"`

---

## Step 3 — Update selector-map.json

After finding the correct selectors, update `references/selector-map.json`:

```json
{
  "version": "X.Y.Z",
  "updated_at": "<current ISO8601 timestamp>",
  "selectors": {
    "open_composer": {
      "primary": "<best selector>",
      "fallbacks": ["<2nd>", "<3rd>", "<xpath>"]
    }
    // ... other actions
  }
}
```
Increment the patch version (`Z`) for selector-only fixes.
Increment minor version (`Y`) if a new action step was added.

---

## Step 4 — Append to History

Append a JSON line to `references/selector-map.history.jsonl`:

```json
{"timestamp": "2026-03-05T08:41:00+07:00", "version": "1.1.0", "action": "open_composer", "old_primary": "...", "new_primary": "...", "reason": "FB redesigned the composer button"}
```

---

## Selector Priority Reference

| Priority | Strategy | Example | Stability |
|---|---|---|---|
| 1 | ARIA / role | `[aria-label="Post"][role="button"]` | ⭐⭐⭐⭐⭐ Most stable |
| 2 | data-* attributes | `[data-testid="composer-post-btn"]` | ⭐⭐⭐⭐ Stable |
| 3 | Text content | `button:has-text("Post")` | ⭐⭐⭐ Medium |
| 4 | XPath | `//div[@role='button'][.='Post']` | ⭐⭐ Last resort |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Script can't find composer | Log in manually, check if FB shows a "Create post" modal instead |
| File input not triggerable | Use `page.set_input_files()` on the hidden input directly after clicking media button |
| Scheduler not appearing | Your account may not have scheduling enabled; try from a desktop browser manually |
| All selectors changed | Run `dom_learner.py --interactive` to step through each action with prompts |
