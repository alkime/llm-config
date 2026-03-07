# Open/Update PR Workflow

Create a pull request with auto-generated description, or update an existing PR's description.

## Workflow

### 1. Gather Branch Information

```bash
# Get current branch name
git branch --show-current

# List commits on this branch vs main
git log main..HEAD --oneline

# Show detailed diff stats
git diff main...HEAD --stat
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

### 3. Analyze Changes

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
gh pr create --title "your title here" --body-file /tmp/claude/pr-body.md
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

- Always use `/tmp/claude/` for temp files (sandbox-safe)
- The `--body-file` flag avoids shell quoting issues with complex markdown
- Ask before overwriting existing descriptions that have content
- `gh pr create` doesn't set local tracking automatically - verify after creation
