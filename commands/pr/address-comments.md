---
name: pr:address-comments
description: Process PR review comments - fetch, validate, fix issues, update style guide
---

Use the `pr` skill to address review comments on a PR.

## PR Selection

1. **If `$ARGUMENTS` contains a PR number** (e.g., `/pr:address-comments 3`), use that PR directly.

2. **If `$ARGUMENTS` is empty**, detect the PR for the current branch:
   ```bash
   gh pr view --json number -q '.number' 2>/dev/null
   ```
   If exactly one PR is found, use it.

3. **If no PR found for the current branch**, list all open PRs and ask:
   ```bash
   gh pr list --json number,headRefName,title
   ```
   Present the list and ask the user which PR to process.

## Worktree Awareness

After selecting a PR, check if the PR's branch has a corresponding worktree:

```bash
git worktree list
```

Match the PR's `headRefName` against worktree branches. If the PR branch maps to a different worktree than the current working directory, inform the user and work in that worktree's directory so file reads and edits target the correct code.
