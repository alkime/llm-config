---
name: epic
description: Turn an approved plan into a tk epic ready for hands-off artificers: Work Streams with branches and bases, Stack declarations, a migrations-first foundation task, verify-* tier tags, human-blocker tasks, and a smoke-test-guide seed. Use after plan approval, before launching artificers.
---

# Epic - Plan to tk Epic

Converts an approved plan (plan mode output, usually sigil-reviewed) into a `tk` epic plus child tasks. The epic is the only handoff to artificers: it must carry everything a stream needs (branches, bases, stacking rules, tiers, blockers). It is also the source for the project->main PR (see the `pr` skill): the Ledger accumulates on it as notes, and its smoke-test seed becomes the Smoke-test guide.

**Hard rule: use the `tk` CLI only.** Never edit `.tickets/*.md` directly. Bodies go in via `-d`/`--design`/`--acceptance` (use `"$(cat file)"` for long text); changes after creation go through `tk add-note`, `tk dep`, `tk status`, etc. Run tk from the repo root of the project that owns the tickets.

## Inputs

- The approved plan file (path), and the project branch name if already chosen.
- The brief/vault note, if any (link it in the epic).

## Workflow

### 1. Optional: plan-reviewer pass

Offer (or run, if the user asked) the `plan-reviewer` agent on the plan before ticketing. It rates each plan section 0/L/M/H by lens and writes a "Sections needing James" summary. Only M/H sections need human attention; fix those in the plan first. Skip for small plans (S-sized streams, no schema, no new API surface). Never ticket from a plan with unresolved M/H sections.

### 2. Decompose into streams

A stream = one worktree = one branch = one PR. Group tasks that touch the same files/packages. Each stream gets a descriptive kebab-case branch (never ticket IDs). Streams should be independent enough to run in parallel; cross-stream order is explicit (`after <stream>`) and also encoded with `tk dep`.

Decide the **project branch** (integration seam): `<kebab-name>`, cut from main in the main checkout, pushed with `-u` to its own remote (never tracking origin/main). Every stream PR targets the project branch (or its stack parent, below). Only the project->main PR targets main. Skip the project branch only for a single-stream epic, in which case say "base: main".

### 3. Declare stacks

Stack declarations replace per-ticket prose like "Stack B 2/3 - based on X". A stack is a chain of branches where each PR targets its parent:

```
main <- parent-branch <- child-branch
```

Rules to state once, in the epic (artificers read them there, not in tickets):
- Child worktree is cut from the parent branch; child PR targets the parent branch (or the project branch for streams not in a stack).
- When the parent merges: retarget the child to the parent's base, `git rebase` (never merge), `git push --force-with-lease`.
- If the project branch itself sits atop another held PR (as resume-revamp sat on assistant-attachments), declare that as an external stack and manage it with `gh stack`; moving the base is `gh stack sync` / `gh stack rebase`, never a merge.
- A stack parent is a **foundation PR**: a HIGH review finding on it interrupts James; elsewhere HIGH goes on the Ledger.

Only declare a stack where the child genuinely needs the parent's code. Otherwise streams are parallel siblings off the project branch.

### 4. Migrations first

All schema work known at plan time goes in **one foundation task, the first task of the first stream**, and every task that touches the new schema depends on it (`tk dep`). Apply once to the shared Supabase (never `db reset`). Rules:
- Additive migrations discovered mid-project: the artificer may add and apply them.
- Rewriting an already-applied migration: create a `human-blocker` "schema rewind" task (reset + replay + reseed) instead; James confirms.
- Privilege/Data-API grants go in `supabase/seed.sql`, never migrations.
- Foundation task tier is at least `verify-integration`.

If the plan has no schema work, omit the task and write "No schema changes" in the epic so the absence is deliberate.

### 5. Tag every task with a verify tier

Exactly one per task (see Tags). Pick the cheapest tier that actually exercises the change:

| Tag | Meaning | Typical |
|-----|---------|---------|
| `verify-cursory` | `make check` only | docs, prompts, refactors with test coverage, config |
| `verify-integration` | + compose up + `INTEGRATION=1` + API checks against the per-worktree ports | handlers, jobs, migrations, RPCs |
| `verify-full` | + iOS simulator smoke under the sim lease | mobile UI, flows crossing client and server |
| `verify-voice` | no automated verification of live duplex; becomes a Ledger/smoke item for James | anything needing real-time voice or ElevenLabs |

A task that is both testable and voice-dependent gets its testable tier plus a `verify-voice` note in its body; use tag `verify-voice` alone only when nothing else can run. Always add the stream tag too (e.g. `ws-<stream>`) and any domain tags (`backend`, `mobile`, ...).

### 6. Human-blocker tasks

Anything an agent cannot or must not do: manual console config (EL agent client events, ASC, Supabase dashboard), secrets (`fly secrets set`), TestFlight uploads, data cleanup on staging/prod, schema rewinds, `make e2e` attestation, calibration sessions. Each is a task tagged `human-blocker` (plus a verify tag, usually `verify-cursory`), with an exact checklist of what to do and what it unblocks. Wire it with `tk dep` so downstream tasks show as blocked. Artificers skip and report these; they never close them.

### 7. Create the epic and tasks

Epic body sections, in order (template: [EPIC_TEMPLATE.md](resources/EPIC_TEMPLATE.md)):

1. One-paragraph goal, plan path, vault link.
2. `## Decisions`
3. `## Work Streams`: per stream: name, branch, base (project branch or stack parent), ordered task chain, size, "after" constraints.
4. `## Stacks` (or "None - all streams are siblings off the project branch")
5. `## Migrations` (foundation task id, or "No schema changes")
6. `## Smoke-test guide (seed)`: the manual steps James runs on the project->main PR, written as checkboxes while planning; artificers append to it via notes, the `pr` skill renders it.
7. `## Before merging to main` (human-only pre-flight, out-of-band ops)
8. `## Out of scope`

```bash
EPIC=$(tk create "Title" -t epic -p 2 --tags <epic-tag> -d "$(cat /tmp/claude/epic-body.md)")
T1=$(tk create "Foundation: migrations" --parent "$EPIC" --tags ws-<stream>,backend,verify-integration \
  -d "<context + approach>" --acceptance "<verifiable conditions>")
tk dep "$T2" "$T1"
```

Every task body states: the stream/branch, base (so the artificer never has to infer it), file paths and patterns, and acceptance criteria that name the tier's checks. Use `tk dep tree $EPIC` to verify the graph has no cycles (`tk dep cycle`) and every stream's first task is reachable.

### 8. Report

Print the epic id, the stream/branch/base table, the human-blocker list, and the first ready tasks. Do not launch artificers unless asked.

## Tags

| Tag | Where | Meaning |
|-----|-------|---------|
| `verify-cursory`/`-integration`/`-full`/`-voice` | task | verification tier, exactly one |
| `human-blocker` | task | human-only; artificers skip |
| `ws-<stream>` | task | stream membership (matches Work Streams) |
| epic tag | epic + tasks | groups an epic's tickets (optional) |

## Dry-run check (pla-ha6d)

Re-deriving "Polish 10.08" from its plan under this template gives: project branch `polish-10.08`; four sibling streams (voice-recall-and-close-logs, mobile-card-polish, talk-button-semantics, duplex-live-captions), `## Stacks: None`, `## Migrations: No schema changes`; tiers: recall prompt = `verify-cursory` (+ `verify-voice` smoke item), already_finalized log = `verify-integration`, card polish and mic semantics = `verify-full`, live captions = `verify-full` + voice smoke item; and a `human-blocker` task "Add vad_score client event to staging + prod EL agents" gating the main PR. Resume Revamp (pla-5c1f) gives the Stack section (assistant-attachments external parent) and the migration foundation (WS-A.1/WS-D.1 collapse into one first task), and WS-F becomes human-blocker tasks.
