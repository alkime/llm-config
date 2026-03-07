# PR Skill

A unified skill for pull request workflows: opening PRs, addressing review comments, learning from feedback, and tracking discovered work.

## What This Skill Does

- **Open/Update PRs** - Generate descriptions from commit history
- **Address Comments** - Validate, fix, and learn from review feedback
- **Style Guide Updates** - Document patterns from recurring feedback
- **Work Discovery** - Capture deferred items as tickets

## When the Skill Activates

Natural language triggers:
- "open a PR", "create a pull request"
- "update the PR description"
- "address the PR comments", "fix the review feedback"
- "what comments are on my PR?"
- "help with my PR"

## File Structure

```
pr/
├── SKILL.md                    # Entry point (agent reads this first)
├── CLAUDE.md                   # Maintenance guide
├── README.md                   # This file (for humans)
├── bin/
│   └── format_pr.py            # Comment fetching script
└── resources/
    ├── OPEN.md                 # Open/update PR workflow
    ├── COMMENTS.md             # Address comments workflow
    ├── STYLE_GUIDE_ANALYSIS.md # Learning from feedback
    └── FOUND_WORK.md           # Capturing work as tickets
```

## PR Lifecycle

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  1. OPEN    │ ──► │  2. ADDRESS COMMENTS │ ──► │  3. FINALIZE    │
│  (once)     │     │  (iterative loop)    │     │  (once)         │
└─────────────┘     └──────────────────────┘     └─────────────────┘
```

### Phase 1: Open/Update PR

1. Gather branch information (commits, diff stats)
2. Check for existing PR
3. Analyze changes
4. Generate description
5. Create or update PR
6. Report result with URL

### Phase 2: Address Review Comments

```
┌──────────────────┐
│  Fetch Comments  │
│  (format_pr.py)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Any unresolved │ NO
│     comments?    ├──────► Phase 3
└────────┬─────────┘
         │ YES
         ▼
┌──────────────────┐
│ Validate against │
│  current code    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Fix confirmed   │
│     issues       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Commit and push  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  More comments   │ YES
│    coming?       ├──────► Loop to Fetch
└────────┬─────────┘
         │ NO
         ▼
      Phase 3
```

### Phase 3: Finalize Review

Always runs when review is complete:

1. **Style Guide Analysis** - Learn from feedback patterns
2. **Track Found Work** - Capture deferred items as tickets

## Requirements

- GitHub CLI (`gh`) authenticated
- Python 3 for the format_pr.py script
- Optional: tickets (`tk`) for work tracking

## Related

- `.opencode/commands/pr/open.md` - Slash command wrapper
- `.opencode/commands/pr/address-comments.md` - Slash command wrapper
- `docs/guides/*.md` - Style guides for the learning loop
