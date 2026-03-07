---
name: docs:update-architecture
description: Update architecture.md based on commits since last update - analyzes changes, proposes updates
---

# Update Architecture Documentation

This command updates `docs/overview/architecture.md` based on changes since it was last modified. It analyzes commits, identifies architectural changes, and proposes documentation updates.

## Workflow

### Phase 1: Find Last Architecture Update

Determine when the architecture doc was last updated:

```bash
# Get the last commit that touched the architecture doc
git log -1 --format="%H|%cs|%s" -- docs/overview/architecture.md
```

Store the commit hash - this is our baseline.

### Phase 2: Gather Changes Since Last Update

1. **Get commit summary:**
   ```bash
   # Count commits since last architecture update
   git rev-list {last_commit}..HEAD --count

   # List commit messages (summarized)
   git log {last_commit}..HEAD --oneline
   ```

2. **Assess scope:**
   - **< 20 commits:** Review all commit messages
   - **20-50 commits:** Group by prefix (feat:, fix:, refactor:) and summarize themes
   - **> 50 commits:** Focus on commits touching key directories (cmd/, internal/, go.mod)

3. **Identify architectural commits:**

   Filter for commits likely to affect architecture:
   ```bash
   # Commits affecting Go package structure
   git log {last_commit}..HEAD --oneline -- "cmd/" "internal/" "pkg/"

   # Dependency changes
   git log {last_commit}..HEAD --oneline -- "go.mod"

   # Config/infrastructure changes
   git log {last_commit}..HEAD --oneline -- "fly.toml" "Dockerfile" "Makefile" "hugo.yaml"
   ```

### Phase 3: Analyze Current State vs Documentation

1. **Read current architecture doc:**
   - Understand what's currently documented
   - Note the section structure

2. **Examine current codebase state:**
   ```bash
   # Package structure
   ls -la cmd/
   ls -la internal/
   ls -la pkg/ 2>/dev/null || echo "No pkg/ directory"
   ```

3. **Compare against documentation:**
   - New packages not mentioned in architecture?
   - Removed packages still documented?
   - Changed workflows or dependencies?
   - New CLI commands or flags?
   - Infrastructure changes (Docker, deployment)?

4. **For significant changes, examine specific commits:**

   Only if needed and commits are reasonably sized:
   ```bash
   # View a specific commit's changes (use sparingly)
   git show {commit_hash} --stat
   ```

### Phase 4: Propose Updates

Present findings to the user:

```
## Architecture Update Analysis

**Last updated:** {date} ({commit_hash})
**Commits since:** {count}

### Detected Changes

1. **New packages/features:**
   - [List any new cmd/, internal/ packages]
   - [New dependencies in go.mod]

2. **Modified workflows:**
   - [Changes to CLI commands]
   - [Changes to build/deploy process]

3. **Removed/deprecated:**
   - [Packages removed]
   - [Features deprecated]

### Proposed Documentation Updates

**Section X - [Name]:**
- Add: [description]
- Update: [description]
- Remove: [description]

Should I apply these updates to docs/overview/architecture.md?
```

**MANDATORY APPROVAL GATE:** After presenting the Phase 4 analysis, you MUST stop and wait for explicit user approval before proceeding. Use AskUserQuestion if the user hasn't responded, or simply wait for their input. Do NOT proceed to Phase 5 without clear confirmation. This ensures the user can review, request modifications, or reject proposed changes.

### Phase 5: Apply Updates (with approval)

If user approves:
1. Use Edit tool to update specific sections
2. Keep the document structure consistent
3. Preserve existing content that's still accurate
4. Update version numbers, dates, or dependency versions as needed

If user wants modifications:
1. Adjust proposed changes
2. Present revised version
3. Repeat until approved

## Key Principles

- **Minimize context usage:** Don't dump entire diffs into context; be selective
- **Focus on architecture:** Skip cosmetic changes, bug fixes, documentation updates
- **Preserve structure:** Keep the existing document organization unless it needs revision
- **User approval required:** Always present changes before applying them
- **Incremental updates:** Better to make small, accurate updates than comprehensive rewrites

## What Constitutes "Architectural Change"

**Include:**
- New packages or commands
- New external dependencies
- Changes to deployment infrastructure
- New environment variables or configuration
- Workflow changes (new build steps, new commands)
- Security configuration changes
- API namespace changes

**Skip:**
- Bug fixes that don't change structure
- Content changes (new blog posts)
- Test additions/changes
- Documentation-only commits (except architecture.md itself)
- Dependency version bumps (unless major version with breaking changes)

## Context Management Tips

If many commits have accumulated:

1. **Start broad:** Read commit messages first, identify themes
2. **Drill down selectively:** Only examine diffs for commits that seem architecturally significant
3. **Use `--stat` first:** See which files changed before reading full diffs
4. **Summarize by area:** "5 commits added TUI support" rather than listing each

If a single massive change (like a migration):

1. Focus on the final state rather than the diff
2. Read the new files directly instead of viewing the diff
3. Understand what was added, not line-by-line what changed
