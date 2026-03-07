# Capturing Discovered Work

PR review comments often surface work that should be tracked but isn't blocking the current PR. Capture these as tickets for later.

## Why Track Found Work

- **Don't lose valuable feedback** - Reviewers have context you may not have later
- **Keep PRs focused** - Address feedback without scope creep
- **Build a backlog** - Surfaced items feed future planning

## Identifying Found Work

Scan all comments (resolved and unresolved) for indicators:

### Explicit Markers
- "TODO:", "FIXME:", "follow-up:"
- "out of scope but...", "nice to have..."
- "we should also...", "consider adding..."

### Implicit Suggestions
- "in the future...", "eventually..."
- "this would be better if..."
- "might want to...", "could also..."
- Suggestions acknowledged but deferred

### User Responses
When the user resolves an AI comment with a response like:
- "Valid point but out of scope - tracking for later"
- "Good idea, will address in a follow-up"
- "Agreed, but too much for this PR"

## Categorizing Items

| Category | Ticket Type | When to Use |
|----------|-------------|-------------|
| Simple improvement | `task` | Single, focused change |
| Bug discovered | `bug` | Defect found during review |
| Larger refactoring | `epic` | Multi-task work needing breakdown |
| Nice-to-have | `task` with priority 3-4 | Lower priority enhancement |

## Creating Tickets

### Simple Task
```bash
tk create "Add rate limiting to auth endpoint" --type=task \
  -d "Source: PR #123 comment by @reviewer on api/handlers/auth.go:45

Original feedback: 'This works but we should add rate limiting later'"
```

### Epic with Children
```bash
# Create parent epic
tk create "Refactor auth to support OAuth" --type=epic

# Create child tasks (use the epic ID from above)
tk create "Research OAuth providers" --type=task --parent=<epic-id>
tk create "Design token storage schema" --type=task --parent=<epic-id>
tk create "Implement OAuth flow" --type=task --parent=<epic-id>
```

## Presenting Findings

Before creating tickets, present findings to the user:

```
Found work from PR comments:

1. [task] "Add rate limiting to auth endpoint"
   Source: Comment by @reviewer on api/handlers/auth.go:45
   "This works but we should add rate limiting later"

2. [epic] "Refactor auth to support OAuth"
   Source: Comment by @reviewer on api/handlers/auth.go:12
   "Consider refactoring auth to support OAuth in the future"
   Suggested breakdown:
   - Research OAuth providers
   - Design token storage schema
   - Implement OAuth flow

3. [task] "Add input validation for email format"
   Source: Your response to AI reviewer dismissing comment
   "Valid point but out of scope - tracking for later"

Create these tickets? [y/n/select]
```

## Reporting Created Tickets

After creation, summarize:

```
Created tickets from PR feedback:
- nw-abc1: Add rate limiting to auth endpoint (task)
- nw-def2: Refactor auth to support OAuth (epic)
  - nw-gh10: Research OAuth providers
  - nw-gh20: Design token storage schema
  - nw-gh30: Implement OAuth flow
```
