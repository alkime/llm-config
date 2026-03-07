# Address Review Comments - Validation Mechanics

How to fetch, validate, and fix PR review comments. See SKILL.md for the overall workflow and when to run end-of-review phases.

## Fetch Comments

```bash
python3 .opencode/skills/pr/bin/format_pr.py [PR_NUMBER]
```

The script groups comments by resolved status (unresolved first) and includes diff hunks.

### Validate Each Unresolved Comment

PR comments are made against a specific commit. The code may have changed since then.

For each **unresolved** comment:

1. **Understand the request**
   - Read comment text and replies
   - Note file path and line number
   - Review the diff hunk (code at time of comment)

2. **Examine current code**
   - Read the actual file now
   - Look beyond the diff hunk at surrounding context
   - Check related files if referenced

3. **Decision matrix**

   | Situation | Action |
   |-----------|--------|
   | Code already addresses concern | Ask user: "Comment says X, code already Y. Skip?" |
   | Clearly needs fixing | Add to TodoWrite list |
   | Ambiguous | Present findings, ask for user judgment |
   | Outdated (API changed, etc.) | Note as outdated, skip |

4. **Create TodoWrite list** of confirmed issues

## Fix Issues

Work through the TodoWrite list systematically:
- Mark items as in_progress
- Make code changes
- Run tests/lint to verify
- Mark completed

## Resolved Comments

Resolved comments don't need fixing but may contain valuable context:

- **User responses to AI reviewers** often explain design decisions
- **Dismissal reasons** can inform style guide updates
- **Deferred items** should be captured as tickets

Example:
```
AI Comment: "Consider using a more descriptive variable name"
User Response: "The name matches our domain terminology per style guide"
→ No fix needed, but confirms style guide pattern
```

## Key Principles

- **Validate before acting** - Comments may reference outdated code
- **User maintains control** - Ask when issues are ambiguous
- **Learn from feedback** - Update style guides for recurring patterns
- **Capture found work** - Don't let valuable suggestions get lost
