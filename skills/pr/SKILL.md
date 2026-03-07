---
name: pr
description: Pull request workflows: open/update PRs with generated descriptions, address review comments with validation, style guide learning, and work discovery. Use for any PR-related task.
---

# PR Skill - Pull Request Lifecycle

Unified skill for the full PR lifecycle: opening PRs, addressing review comments, learning from feedback, and tracking discovered work.

## Prerequisites

```bash
# Required: GitHub CLI authenticated
gh auth status

# Required: Python 3 for comment fetching
python3 --version

# Optional: tickets for tracking discovered work
tk help
```

## PR Lifecycle

Three phases, typically sequential: Open → Address Comments (iterative) → Finalize

### Phase 1: Open PR

Create or update a pull request description.

**Triggers:** "open a PR", "create a pull request", "update PR description"

**→ Load [OPEN.md](resources/OPEN.md) for detailed workflow**

### Phase 2: Address Comments

Fetch, validate, and fix review feedback. This phase repeats as reviewers add comments.

**Triggers:** "address the PR comments", "fix review feedback", "what comments are on my PR?"

**Steps:**

1. **Fetch comments** - Use `format_pr.py` to get all PR comments grouped by status
2. **Validate** - For each unresolved comment, check if it still applies to current code
3. **Fix** - Address confirmed issues using TodoWrite to track progress
4. **Commit and push** - One commit per round of fixes is fine
5. **Loop or proceed** - If more comments coming, loop back; otherwise proceed to Phase 3

**→ Load [COMMENTS.md](resources/COMMENTS.md) for validation mechanics and decision matrix**

### Phase 3: Finalize Review

Complete the PR lifecycle with learning and work capture. Always run when review is complete.

**Triggers:** "finalize the PR", "we're done with review", "let's wrap up", or no unresolved comments remain

**CRITICAL: Work in the PR branch, not main.** All Phase 3 work (style guide updates, commits) MUST be done in the PR's feature branch. This associates the learning with the code that prompted it and keeps the PR as the unit of work.

**Steps:**

1. **Ensure you're in the PR branch** - Check out the feature branch or worktree before making changes
2. **Style Guide Analysis** - Analyze feedback patterns for documentation gaps, propose updates
3. **Found Work Capture** - Scan comments for deferred items, create tickets for approved work
4. **Commit and push to the PR branch** - Style guide updates become part of the PR

These steps always run but may not produce output if there are no patterns to document or work to track.

**→ Load [STYLE_GUIDE_ANALYSIS.md](resources/STYLE_GUIDE_ANALYSIS.md) and [FOUND_WORK.md](resources/FOUND_WORK.md)**

## Determining Current Phase

| Situation | Phase |
|-----------|-------|
| No PR exists | Phase 1 |
| PR exists, unresolved comments | Phase 2 |
| PR exists, user signals "done with review" | Phase 3 |
| PR exists, no unresolved comments | Phase 3 |
| Uncertain | Ask user: "Are you looking to open a PR, address comments, or finalize?" |

## Shared Context

### GitHub CLI Patterns

```bash
# Check for existing PR on current branch
gh pr view --json number,title,body,state 2>/dev/null

# Get PR number
gh pr view --json number -q '.number'

# Create PR with body from file
gh pr create --title "title" --body-file /tmp/claude/pr-body.md

# Update existing PR
gh pr edit --body-file /tmp/claude/pr-body.md
```

### Branch Detection

```bash
# Current branch
git branch --show-current

# Check if tracking remote
git rev-parse --abbrev-ref @{upstream} 2>/dev/null

# Commits since main
git log main..HEAD --oneline

# Diff stats
git diff main...HEAD --stat
```

### PR Discovery (Multi-Worktree)

When the current branch has no PR, or a specific PR number is provided:

```bash
# List all open PRs with branch info
gh pr list --json number,headRefName,title

# List worktrees to match PR branches to directories
git worktree list
```

Match each PR's `headRefName` to a worktree branch. When working on a PR that belongs to a different worktree, operate in that worktree's directory so file reads and edits target the correct code.

### Temp File Pattern

Always use `/tmp/claude/` for temp files (sandbox-safe):
```bash
mkdir -p /tmp/claude
cat > /tmp/claude/pr-body.md << 'EOF'
...content...
EOF
```

### Style Guides

Map file types to style guides for the learning loop:

| Files | Style Guide |
|-------|-------------|
| `*.go` | `docs/guides/go-style-guide.md` |
| `*.ts`, `*.tsx` | `docs/guides/react-typescript-style-guide.md` |
| `Dockerfile*`, `Makefile`, `.github/**` | `docs/guides/infra-style-guide.md` |

## Resources

| Resource | Content |
|----------|---------|
| [OPEN.md](resources/OPEN.md) | Open/update PR description workflow |
| [COMMENTS.md](resources/COMMENTS.md) | Validation mechanics for review comments |
| [STYLE_GUIDE_ANALYSIS.md](resources/STYLE_GUIDE_ANALYSIS.md) | Learning from feedback patterns |
| [FOUND_WORK.md](resources/FOUND_WORK.md) | Capturing discovered work as tickets |

## Script Reference

The bundled `bin/format_pr.py` script fetches PR comments:
```bash
python3 .opencode/skills/pr/bin/format_pr.py [PR_NUMBER]
```
- Uses GitHub GraphQL API via `gh` CLI
- Auto-detects PR from current branch
- Groups by resolved status (unresolved first)
- Includes diff hunks and reply threads
