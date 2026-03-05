# 📚 Documentation Index

**Repo:** `ptadigi/facebook-personal-ai-automation` · **Version:** 2.1.0 · **Updated:** 2026-03-05

Central navigation map for all documentation in this repository.

---

## 🚀 Getting Started

| | |
|---|---|
| [README.md](../README.md) | Project overview, quickstart, FAQ |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Development setup, how to contribute |
| [CHANGELOG.md](../CHANGELOG.md) | Version history and release notes |

---

## 🤖 Agent Integration Guides

For teams and individuals integrating AI agents with this skill:

| Guide | Description |
|---|---|
| [USAGE_MULTI_AGENT.md](USAGE_MULTI_AGENT.md) | Decision matrix: which agent to use when, orchestration patterns, shared error protocol |
| [agent-guides/clawbot.md](agent-guides/clawbot.md) | Clawbot integration: Vietnamese/English triggers, validation, error runbook |
| [agent-guides/claude-code.md](agent-guides/claude-code.md) | Claude Code integration: MCP tool schema, bash_tool usage, output parsing |
| [agent-guides/antigravity.md](agent-guides/antigravity.md) | Antigravity integration: SKILL.md loading, run_command patterns, parse_output |

---

## 🧪 Testing & Quality Assurance

| Document | Description |
|---|---|
| [acceptance-tests/multi-agent-uat.md](acceptance-tests/multi-agent-uat.md) | 26 UAT test cases covering contract parity, per-agent validation, and regression guards |
| [clawbot-acceptance-tests.md](clawbot-acceptance-tests.md) | Detailed Clawbot acceptance test matrix (happy path, error path, edge cases) |

---

## 🔒 Security

| Document | Description |
|---|---|
| [security-audit.md](security-audit.md) | Full security audit: 20 findings across 7 categories (Security, Reliability, Observability, Architecture, Performance, Maintainability, Compliance) |
| [../SECURITY.md](../SECURITY.md) | How to report vulnerabilities responsibly |

---

## 🗺️ Roadmap

| Document | Description |
|---|---|
| [ROADMAP_NEXT_FEATURES.md](ROADMAP_NEXT_FEATURES.md) | 15 planned features: Quick Wins, Mid-term, Advanced — each with effort, risk, and done criteria |

---

## 📁 Repository Structure

```
facebook-personal-ai-automation/
├── scripts/                    # Runtime scripts (do not modify without testing)
│   ├── post.py                 # Main posting script
│   ├── account_manager.py      # Account init/test/list
│   ├── proxy_manager.py        # Proxy add/health
│   ├── scheduler.py            # Queue-based scheduler daemon
│   ├── dom_learner.py          # Self-healing selector discovery
│   ├── fingerprint_gen.py      # Browser fingerprint generator
│   └── lib/cookies.py          # Shared cookie handling
│
├── skills/                     # AI agent skill definitions
│   ├── clawbot-skill.md        # Clawbot action catalog + runbook
│   ├── claude-skill.md         # Claude Code tool schema
│   └── antigravity-skill.md   # Antigravity SKILL.md format
│
├── docs/                       # This directory
│   ├── INDEX.md                ← You are here
│   ├── USAGE_MULTI_AGENT.md
│   ├── ROADMAP_NEXT_FEATURES.md
│   ├── security-audit.md
│   ├── clawbot-acceptance-tests.md
│   ├── agent-guides/
│   │   ├── clawbot.md
│   │   ├── claude-code.md
│   │   └── antigravity.md
│   └── acceptance-tests/
│       └── multi-agent-uat.md
│
├── accounts/                   # (gitignored) Per-account data
│   └── <account_id>/
│       ├── cookies.json        # Facebook session cookies (0o600)
│       └── fingerprint.json    # Browser fingerprint
│
├── references/                 # Runtime data
│   ├── selector-map.json       # Current Facebook DOM selectors
│   ├── run-log.jsonl           # Structured operation log
│   └── schedule-queue.json     # Pending scheduled posts
│
├── tests/                      # pytest unit tests (48 tests)
├── .github/workflows/ci.yml    # GitHub Actions CI
├── Makefile                    # Dev commands
├── requirements.txt            # Pinned dependencies
└── config.example.json         # Example configuration
```

---

## 🔗 Quick Links

- **Bug report:** [GitHub Issues](https://github.com/ptadigi/facebook-personal-ai-automation/issues/new?template=bug_report.md)
- **Feature request:** [GitHub Issues](https://github.com/ptadigi/facebook-personal-ai-automation/issues/new?template=feature_request.md)
- **CI status:** [GitHub Actions](https://github.com/ptadigi/facebook-personal-ai-automation/actions)
- **PRs:** [Pull Requests](https://github.com/ptadigi/facebook-personal-ai-automation/pulls)
