---
name: epic
description: Turn an approved plan into a tk epic ready for hands-off artificers: Work Streams with branches and bases, Stack declarations, a migrations-first foundation task, verify-* tier tags, human-blocker tasks, and a smoke-test-guide seed. Use after plan approval, before launching artificers.
---

# Epic - Plan to tk Epic

Converts an approved plan (plan mode output, usually plan-reviewed) into a `tk` epic plus child tasks. The epic is the only handoff to artificers: it must carry everything a stream needs (branches, bases, stacking rules, tiers, blockers). It is also the source for the project->main PR (see the `pr` skill): the Ledger accumulates on it as notes, and its smoke-test seed becomes the Smoke-test guide.

**Hard rule: use the `tk` CLI only.** Never edit `.tickets/*.md` directly. Bodies go in via `-d`/`--design`/`--acceptance` (use `"$(cat file)"` for long text); changes after creation go through `tk add-note`, `tk dep`, `tk status`, etc. Run tk from the repo root of the project that owns the tickets.

## Inputs

- The approved plan file (path), and the project branch name if already chosen.
- The brief/vault note, if any (link it in the epic).
- The project's verification conventions (below).

## Project conventions

The skill is project-agnostic: tier names and the pipeline are fixed here; what each tier *runs* belongs to the project. Before ticketing, find the project's verify-tier definitions: a "Verify tiers" section in its `CLAUDE.md` or `AGENTS.md`, or the doc such a section points to (Penny's AGENTS.md "Verifying in a worktree" points to `docs/runbooks/worktree-verification.md`). Read from it: the gate command (the full check before a PR, e.g. `make check`), the worktree bootstrap, what `verify-integration` and `verify-full` run, how schema changes are applied, and the hard rules for shared resources.

If the project defines no tiers, ask James for the gate command and which tiers apply (a project with no client app has no `verify-full`). Write his answers into the epic body as a `## Verification` section so artificers have them, and offer to add a "Verify tiers" section to the project's `CLAUDE.md` so the next epic doesn't need to ask.

## Workflow

### 1. Optional: plan-reviewer pass

Offer (or run, if the user asked) the `plan-reviewer` agent on the plan before ticketing, ideally before James reads it. It sorts findings into author fixes (applied without asking James) and asks (callouts in the sections where James must decide), then the plan opens in plannotator-tui beside the chat. Follow the agent's "Resolution" section. Skip for small plans (S-sized streams, no schema, no new API surface). Never ticket from a plan with unresolved findings: a `plan-review:start` block or any `plan-review:ask` callout still in the plan means unresolved; a one-line `plan-review: applied` marker means resolved.

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
- If the project branch itself sits atop another held PR, declare that as an external stack and manage it with `gh stack`; moving the base is `gh stack sync` / `gh stack rebase`, never a merge.
- A stack parent is a **foundation PR**: a HIGH review finding on it interrupts James; elsewhere HIGH goes on the Ledger.

Only declare a stack where the child genuinely needs the parent's code. Otherwise streams are parallel siblings off the project branch.

### 4. Migrations first

All schema work known at plan time goes in **one foundation task, the first task of the first stream**, and every task that touches the new schema depends on it (`tk dep`). How migrations are applied is the project's (a shared dev database applied once, or a local file the app migrates itself); follow its docs. Rules:
- Additive migrations discovered mid-project: the artificer may add and apply them.
- Rewriting an already-applied migration, where that would destroy shared data: create a `human-blocker` "schema rewind" task (the project's reset + replay + reseed) instead; James confirms. Where each worktree's database is its own and disposable, a rewrite is ordinary work.
- Foundation task tier is at least `verify-integration` (or the project's highest automated tier, if lower).

If the plan has no schema work, omit the task and write "No schema changes" in the epic so the absence is deliberate.

### 5. Tag every task with a verify tier

Exactly one per task (see Tags). Pick the cheapest tier that actually exercises the change. The project's docs say what each tier runs; the general shape:

| Tag | Meaning | Typical |
|-----|---------|---------|
| `verify-cursory` | the project's gate only | docs, prompts, refactors with test coverage, config |
| `verify-integration` | + the app running on the worktree's own ports/data, checked through its API or CLI | handlers, jobs, migrations, adapters |
| `verify-full` | + an end-to-end smoke in a real client (simulator, browser) | client UI, flows crossing client and server |
| `verify-voice` | can't be verified by an agent (live voice, real hardware, a person's judgment); becomes a smoke item for James | anything needing real-time voice or a physical device |

A task that is both testable and needs a human check gets its testable tier plus a `verify-voice` note in its body; use tag `verify-voice` alone only when nothing else can run. Always add the stream tag too (e.g. `ws-<stream>`) and any domain tags (`backend`, `mobile`, ...).

Also add one review tier tag (`review-standard` or `review-deep`) beside the verify tag. Use `review-deep` when the task's PR is stacked-upon (a foundation PR), touches migrations/schema, touches auth/RBAC, or will exceed ~800 changed lines; otherwise `review-standard`. The artificer passes the tier to the code-reviewer; where a stream's tasks differ, the deepest tier wins for the stream's PR.

### 6. Human-blocker tasks

Anything an agent cannot or must not do: config in a third-party dashboard, setting deploy secrets, app-store uploads, data cleanup on staging/prod, schema rewinds, the project's e2e attestation, calibration sessions. Each is a task tagged `human-blocker` (plus a verify tag, usually `verify-cursory`), with an exact checklist of what to do and what it unblocks. Wire it with `tk dep` so downstream tasks show as blocked. Artificers skip and report these; they never close them.

### 7. Create the epic and tasks

Epic body sections, in order (template: [EPIC_TEMPLATE.md](resources/EPIC_TEMPLATE.md)):

1. One-paragraph goal, plan path, vault link.
2. `## Decisions`
3. `## Work Streams`: per stream: name, branch, base (project branch or stack parent), ordered task chain, size, "after" constraints.
4. `## Stacks` (or "None - all streams are siblings off the project branch")
5. `## Migrations` (foundation task id, or "No schema changes")
6. `## Verification`, only when the project's docs define no tiers (see Project conventions)
7. `## Smoke-test guide (seed)`: the manual steps James runs on the project->main PR, written as checkboxes while planning; artificers append to it via notes, the `pr` skill renders it.
8. `## Before merging to main` (human-only pre-flight, out-of-band ops)
9. `## Out of scope`

```bash
EPIC=$(tk create "Title" -t epic -p 2 --tags <epic-tag> -d "$(cat /tmp/claude/epic-body.md)")
T1=$(tk create "Foundation: migrations" --parent "$EPIC" --tags ws-<stream>,backend,verify-integration \
  -d "<context + approach>" --acceptance "<verifiable conditions>")
tk dep "$T2" "$T1"
```

Every task body states: the stream/branch, base (so the artificer never has to infer it), file paths and patterns, and acceptance criteria that name the tier's checks. Use `tk dep tree $EPIC` to verify the graph has no cycles (`tk dep cycle`) and every stream's first task is reachable.

### 8. Report

Print the epic id, the stream/branch/base table, the human-blocker list, and the first ready tasks. Do not launch artificers unless asked.

### 9. Launch and supervise artificers (when asked)

Launch one `artificer` per stream in a single message (background). Then this session is the **foreman**: artificers' own background waits don't reliably wake them, so stalls go unnoticed unless you watch. Run [`scripts/foreman.sh`](scripts/foreman.sh) from the project's main checkout:

```bash
~/.claude/skills/epic/scripts/foreman.sh <project-branch> <stream-branch>…
```

It prints one line per stream (head commit and age, PR state and base), one per held sim-lease slot (none for projects that don't use the `ios-sim` lease), and a last line `ALL MERGED` or `RUNNING`. Lines needing action start with `!`. Arm it with the Monitor tool (`timeout_ms` 1800000), emitting only new `!` lines and the finish:

```bash
F=~/.claude/skills/epic/scripts/foreman.sh; prev=""
while true; do
  out="$("$F" <project-branch> <stream-branch>… 2>&1)"
  cur="$(grep '^!' <<<"$out" | sed 's/([0-9]*m ago)//; s/for [0-9]*s since/since/' | sort)"
  comm -13 <(echo "$prev") <(echo "$cur")
  prev="$cur"
  grep -qx 'ALL MERGED' <<<"$out" && { echo "ALL MERGED"; break; }
  sleep 300
done
```

On each event, SendMessage the stream's artificer (and re-arm the Monitor whenever it expires, until `ALL MERGED`):
- `! STALLED` (head unchanged 45m): ask for status. Is it blocked, waiting on something, or done and idle?
- `! LEASE` (slot held 20m+): tell the holder to finish the sim step and release (`~/.claude/skills/ios-sim/sim-lease.sh release`) now.
- `! REBASE` (stack parent merged): tell the child to rebase onto the parent's base per the Stacks rules.

Thresholds: `FOREMAN_STALL_MIN`, `FOREMAN_LEASE_MIN`.

## Tags

| Tag | Where | Meaning |
|-----|-------|---------|
| `verify-cursory`/`-integration`/`-full`/`-voice` | task | verification tier, exactly one |
| `review-standard`/`review-deep` | task | code-reviewer tier, exactly one (default `review-standard`): single lens pass + correctness subagent + judge. `review-deep` = shared-context fan-out, one subagent per lens. |
| `human-blocker` | task | human-only; artificers skip |
| `ws-<stream>` | task | stream membership (matches Work Streams) |
| epic tag | epic + tasks | groups an epic's tickets (optional) |
