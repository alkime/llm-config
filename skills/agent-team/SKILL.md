---
name: agent-team
description: "Coordinated multi-agent teams for complex work. Sub-skills: (1) Architecture Design Team — produces a full technical design package from an architecture brief (systems design, API design, implementation plan, client architecture, review), then creates a tk epic for execution. (2) Build Team — executes an epic's work streams in parallel using isolated worktrees with validation."
---

# Agent Team — Coordinated Multi-Agent Workflows

Orchestrate specialized agent teams that work in dependency order to produce high-quality deliverables. Each sub-skill defines a team roster, dependency graph, and coordination protocol.

## Sub-Skills

### `/agent-team design` — Architecture Design Team

Produces a complete technical design package from an architecture brief or feature specification. Spawns specialized agents (systems architect, API designer, backend/client engineers, domain specialist, adversarial reviewer) in dependency waves, tracks progress via tasks, and synthesizes findings into an executive summary. Optionally creates a `tk` epic with work streams and tasks for handoff to the Build Team.

**Triggers:** "design the system", "produce a technical design", "I have an architecture brief", "create a design package"

**Load [DESIGN_TEAM.md](resources/DESIGN_TEAM.md) for the full workflow.**

### `/agent-team build` — Build Team

Executes an epic's work streams in parallel. One builder agent per work stream, each in its own git worktree. A validator agent runs `make check` after each task. The team lead coordinates cross-stream dependencies, rebases, and creates PRs. Uses the `tk` CLI for task state (`tk ready`, `tk start`, `tk close`).

**Triggers:** "implement the design", "build from the plan", "execute the epic", "run the build team on {epic-id}"

**Load [BUILD_TEAM.md](resources/BUILD_TEAM.md) for the full workflow.**

## Determining Which Sub-Skill

| User Intent | Sub-Skill |
|-------------|-----------|
| Has a brief/spec, wants design documents | `design` |
| Has design docs or tickets, wants code | `build` |
| Wants both (brief → design → code) | Run `design` first, then `build` from its output |
| Has a `tk` epic, wants to execute it | `build` |
| Unclear | Ask: "Are you looking to design (produce documents) or build (write code)?" |

## The Design → Build Pipeline

The two sub-skills compose naturally:

1. `/agent-team design` produces design docs + a `tk` epic with work streams
2. `/agent-team build` reads the epic and executes the work streams in parallel

The epic is the handoff artifact. It contains work streams (with branch names), task chains (with dependencies), and references to the design docs. The Build Team's builders read the task tickets for their implementation blueprints.

## Core Principles (All Sub-Skills)

These apply to every agent team workflow:

1. **Dependency-ordered spawning** — never launch an agent before its inputs exist.
2. **Wave-based parallelism** — launch all agents in a wave simultaneously. Don't serialize when you can parallelize.
3. **Resource management** — shut down agents as soon as their work is done and no downstream agent needs them.
4. **Visible progress** — update the user with a status table after each wave completes.
5. **Rich agent prompts** — brief each agent like a smart colleague who just walked in. Include role, deliverable, context files to read, detailed section outline, codebase patterns to follow, and who to notify on completion.
6. **Use `tk` for task state** — `tk ready`, `tk start`, `tk close`, `tk dep`. The ticket system is the canonical source of truth for task ordering and status.
