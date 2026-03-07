# Style Guide Gap Analysis

After addressing PR comments, analyze the feedback for patterns that should be documented in style guides.

## CRITICAL: Work in the PR Branch

**All style guide updates MUST be committed to the PR's feature branch, NOT main.**

Before making any changes:
1. Verify you're in the correct branch: `git branch --show-current`
2. If in main or wrong branch, switch to the PR branch or its worktree
3. Style guide updates are part of the PR - they ship with the code that prompted them

This ensures:
- Learning is associated with the code changes that prompted it
- Style guide updates go through the same review process
- The PR is a complete unit of work (code + documentation)

## Purpose

PR feedback often reveals:
- Undocumented conventions
- Edge cases not covered by guides
- Decision rationale that should be recorded
- Anti-patterns to avoid

## Analysis Process

### 1. Determine Relevant Guides

Map file types to style guides:

| Files Touched | Style Guide |
|--------------|-------------|
| `*.go`, `api/**` | `docs/guides/go-style-guide.md` |
| `*.ts`, `*.tsx`, `clients/**` | `docs/guides/react-typescript-style-guide.md` |
| `Dockerfile*`, `Makefile`, `.github/**`, `fly.toml`, `*.sh` | `docs/guides/infra-style-guide.md` |

Multiple guides may be relevant for a single PR.

### 2. Read Current Guide(s)

For each relevant guide, read its current contents to understand what's already documented.

### 3. Identify Gaps

Review both:
- **Fixed comments** - What patterns needed correcting?
- **Resolved comments with responses** - What decisions were explained?

Look for:
- Patterns that apply broadly (not one-off fixes)
- Recurring themes across comments
- User explanations of "why we do X not Y"

### 4. Evaluate for Inclusion

| Include If... | Skip If... |
|--------------|-----------|
| Pattern applies to future code | One-time edge case |
| Multiple comments on same theme | Already documented differently |
| User explained decision rationale | Context-specific choice |
| Prevents future review cycles | Minor stylistic preference |

### 5. Report Findings

**If guide already covers patterns:**
```
Style guide analysis: All feedback patterns are already documented. No updates needed.
```

**If gaps found:**
```
Style guide gap analysis:

## go-style-guide.md
- Gap 1: [Pattern] -> Missing from guide
- Gap 2: [Pattern from user response] -> Rationale should be documented

Proposed additions:
[Specific text to add]

Should I update the style guide(s)?
```

### 6. Update If Approved

**Ensure you're in the PR branch before editing:**
```bash
# Verify branch
git branch --show-current  # Should be feature branch, not main

# If using worktree, cd to it first
cd .worktrees/<feature-name>
```

Then:
- Add new guidelines to appropriate section
- Include rationale when available
- Keep additions concise and actionable
- Follow existing guide format
- Commit to the PR branch and push

## Example Gap Analysis

PR feedback pattern:
```
Comment: "Wrap errors with context"
Comment: "Use fmt.Errorf with %w"
User response: "We always wrap - it's in our style guide"
```

Analysis:
- Check if go-style-guide.md documents error wrapping
- If not, propose addition:
  ```markdown
  ### Error Handling
  Always wrap errors with context using `fmt.Errorf`:
  ```go
  if err != nil {
      return fmt.Errorf("loading config: %w", err)
  }
  ```
  ```
