---
name: a-team-build
description: "Build Team — executes an epic's work streams in parallel using isolated worktrees with validation. One builder per work stream, coordinated by a team lead."
model: sonnet
---

# A-Team Build — Parallel Epic Execution

Executes an epic's work streams in parallel. One builder agent per work stream, each in its own git worktree. A validator agent runs `make check` after each task. The team lead coordinates cross-stream dependencies, rebases, and creates PRs. Uses the `tk` CLI for task state (`tk ready`, `tk start`, `tk close`).

**Triggers:** "implement the design", "build from the plan", "execute the epic", "run the build team on {epic-id}"

**Load [BUILD_TEAM.md](resources/BUILD_TEAM.md) for the full workflow.**

## See Also

- [`/a-team`](../a-team/SKILL.md) — Architecture Design Team (produces the design package and epic that this skill consumes)
