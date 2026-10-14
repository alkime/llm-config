# Open/Update PR Workflow

Create a pull request with auto-generated description, or update an existing PR's description.

## Workflow

### 1. Determine the Base Branch

Never assume `main`. Resolve `BASE` in this order, first hit wins:

```bash
HEAD_BRANCH=$(git branch --show-current)

# 1. Existing PR for this branch: keep its base
BASE=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null)

# 2. gh stack extension: the stack parent of this branch
[ -z "$BASE" ] && gh stack view 2>/dev/null   # read the parent of $HEAD_BRANCH from the output, if installed and in a stack

# 3. Epic: the stream's `base:` in the epic's Work Streams, or its project branch
#    (tk show <epic>; the user or the task body names the epic)

# 4. Branch upstream relationship: the nearest ancestor branch with a remote
#    git merge-base against candidate project/stack branches; pick the one with the fewest commits ahead

# 5. Fallback: main (say so in the output)
```

State the chosen base and why before creating the PR. If sources 1-3 disagree (e.g. epic says project branch but the worktree was cut from main), stop and ask. A stream PR must never silently target main when the epic names a project branch.

**Project->main mode:** if `BASE` is `main` and `HEAD_BRANCH` is an epic's project branch, load [LEDGER.md](LEDGER.md) and use its body instead of Step 4's template.

Then gather the diff against `$BASE`:

```bash
git log origin/$BASE..HEAD --oneline
git diff origin/$BASE...HEAD --stat
```

### 2. Check for Existing PR

```bash
gh pr view --json number,title,body,state 2>/dev/null
```

**If PR exists:**
- Check if the body is empty or minimal
- If body has content, ask user: "This PR already has a description. Would you like to overwrite it?"
- If user confirms or body is empty, proceed to update flow (Step 5b)
- If user declines, stop

**If no PR exists:**
- Check if branch has been pushed: `git rev-parse --abbrev-ref @{upstream} 2>/dev/null`
- If not pushed, push first: `git push -u origin $(git branch --show-current)`
- Proceed to create flow (Step 5a)

### 3. Analyze Changes (against `$BASE`)

Review the commits and changes to understand:
- What was added, removed, or modified
- The overall theme/purpose of the changes
- Any notable statistics (files changed, lines added/removed)

### 4. Generate Description

Write the PR description to a temp file:

```bash
mkdir -p /tmp/claude
cat > /tmp/claude/pr-body.md << 'PREOF'
## Summary

- Bullet point 1
- Bullet point 2
- Bullet point 3

## Test plan

- [ ] Test item 1
- [ ] Test item 2

Generated with [Claude Code](https://claude.ai/code)
PREOF
```

### 5a. Create New PR

```bash
gh pr create --base "$BASE" --title "your title here" --body-file /tmp/claude/pr-body.md
```

**Important:** After creating, verify tracking is set up:
```bash
git rev-parse --abbrev-ref @{upstream} 2>/dev/null || \
  git branch --set-upstream-to=origin/$(git branch --show-current)
```

### 5b. Update Existing PR

```bash
gh pr edit --body-file /tmp/claude/pr-body.md
```

Optionally update the title too:
```bash
gh pr edit --title "improved title" --body-file /tmp/claude/pr-body.md
```

### 6. Report Result

Output the PR URL so the user can review it.

## PR Description Guidelines

- **Title:** Use conventional commit format (feat:, fix:, chore:, docs:, refactor:)
- **Summary:** 3-5 bullet points covering the key changes
- **Stats:** Include net line changes if significant (e.g., "Net change: -2,333 lines")
- **Test plan:** List verification steps as checkboxes

## Notes

- For stacked PRs, add "Stack: based on `<parent-branch>` (n/m)" to the Summary; when the parent merges, retarget (`gh pr edit --base`) and `git rebase`, never merge.
- Write `.sigil/review-order.yaml` locally if the project uses sigil review (never commit it).
- Always use `/tmp/claude/` for temp files (sandbox-safe)
- The `--body-file` flag avoids shell quoting issues with complex markdown
- Ask before overwriting existing descriptions that have content
- `gh pr create` doesn't set local tracking automatically - verify after creation
