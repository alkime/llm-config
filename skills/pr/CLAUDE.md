# PR Skill Maintenance Guide

## Purpose

This skill provides a unified workflow for pull request lifecycle:
- **Open/Update PRs** with auto-generated descriptions
- **Address review comments** with validation, fixing, and learning
- **Style guide updates** from feedback patterns
- **Work discovery** capturing deferred items as tickets

## File Structure

```
pr/
├── SKILL.md                    # Entry point, shared context, workflow selection
├── CLAUDE.md                   # This file - maintenance guide
├── README.md                   # Human documentation
├── bin/
│   └── format_pr.py            # Bundled comment fetching script
└── resources/
    ├── OPEN.md                 # Open/update PR description workflow
    ├── COMMENTS.md             # Address review comments workflow
    ├── STYLE_GUIDE_ANALYSIS.md # Learning from feedback
    └── FOUND_WORK.md           # Capturing discovered work as tickets
```

## Key Dependencies

- `gh` CLI - GitHub API access (required)
- `python3` - For format_pr.py script (required)
- `tk` - Tickets CLI for work tracking (optional)
- `docs/guides/*.md` - Style guides for the learning loop

## When to Update

### SKILL.md
- Shared context changes (gh CLI patterns, branch detection)
- Workflow selection logic changes
- Prerequisites change

### resources/OPEN.md
- PR description format changes
- Create/update flow changes
- Title conventions change

### resources/COMMENTS.md
- Validation workflow changes
- Phase structure changes

### resources/STYLE_GUIDE_ANALYSIS.md or FOUND_WORK.md
- Pattern recognition logic changes
- Ticket creation workflow changes

## Testing Changes

```bash
# Verify SKILL.md word count (target: 400-600 words)
wc -w .opencode/skills/pr/SKILL.md

# Verify script works
python3 .opencode/skills/pr/bin/format_pr.py --help 2>&1 || python3 .opencode/skills/pr/bin/format_pr.py

# Test workflow selection triggers:
# - "open a PR" → should load OPEN.md
# - "address PR comments" → should load COMMENTS.md
```

## Design Decisions

### Unified vs Separate Skills

This skill combines "open PR" and "address comments" because:
1. They share significant context (gh CLI, branch detection, temp file patterns)
2. They're phases of the same lifecycle
3. One skill means one description for better triggering
4. Post-comment-fixes, users often want to update the PR description

### Conditional Workflows

The SKILL.md uses workflow selection pattern:
- Entry point has shared context
- Branches to resource files based on user intent
- Resources are self-contained for their workflow
