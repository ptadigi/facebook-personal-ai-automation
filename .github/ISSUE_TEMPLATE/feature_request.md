---
name: Feature Request
about: Suggest a new feature or enhancement
title: '[FEAT] '
labels: enhancement
assignees: ''
---

## Feature Summary

A clear, one-line description of the feature you'd like to see.

## Problem Statement

What problem are you trying to solve? Why is this needed?

> Example: "When multiple accounts hit RATE_LIMIT simultaneously, there's no coordinated backoff — they all retry at the same time and compound the issue."

## Proposed Solution

Describe what you'd like to happen or how you imagine the feature working.

```bash
# Example: new flag you'd like
python scripts/scheduler.py --backoff-strategy=exponential --max-backoff=120
```

## Alternatives Considered

What other approaches did you consider? Why weren't they sufficient?

## Relation to Roadmap

Is this already in [ROADMAP_NEXT_FEATURES.md](../../docs/ROADMAP_NEXT_FEATURES.md)? If so, which feature ID (F01-F15)?

- [ ] Yes, this is feature: `F__`
- [ ] No, this is a new idea

## Impact

| Dimension | Assessment |
|---|---|
| Affects output contract? | Yes / No |
| Requires new dependency? | Yes / No — which? |
| Breaking change? | Yes / No |
| Estimated complexity | Small (< 1 day) / Medium (1 week) / Large (1+ month) |

## Additional Context

Any mockups, log examples, or references that help explain the feature.
