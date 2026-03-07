---
name: qtk
description: Quick add an idea or task to the backlog
---

# Quick Backlog Entry

Add the argument text as a backlog task. For quick capture of ideas without breaking flow.

**Defaults:** `--type=task --priority=2 --tags=backlog`

## Execution

1. Create the ticket: `tk create "$ARGUMENTS" --type=task --priority=2 --tags=backlog`
2. Report: "Added `<id>`: <title>"

No prompts needed - just execute and confirm.

## Finding Quick Ideas Later

```bash
tk list --tags=backlog
```
