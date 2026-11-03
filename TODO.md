# TODO

A running list of llm-config changes waiting to be made. Add new items at the bottom of their section. Delete an item once it lands; git history keeps the record.

## Pipeline: lessons from the Notifications Iteration run (2026-10-14/15)

Source: the first full epic run on the new pipeline (platform epics `pla-dfvy` and `pla-zv04`, 4 stream PRs #350–#353). Each item names the failure it fixes.

### Foreman monitoring (orchestrator side)

- [ ] Platform: one-line pointer in `AGENTS.md`, pipeline step 3, to the epic skill's "Launch and supervise artificers" step.

### Sim lease

- [ ] **Platform cutover to the shared `~/.claude/skills/ios-sim/sim-lease.sh`** (it has slots now: `SIM_LEASE_SLOTS`, default 2). `scripts/sim-lease.sh` becomes a one-line `exec` wrapper; repoint `AGENTS.md` and `docs/runbooks/worktree-verification.md` (which still describe the single `Penny Agent` sim). The old `Penny Agent` simulator can be deleted once nothing uses it.
  - Prerequisite (in progress in platform, 2026-10-15): the sim `flutter run` targets pass `-d $SIM_UDID`. Without it, a second booted sim makes `flutter run` pick the wrong device.

### `agents/artificer.md`

- [ ] **No background waits at the end of a turn.** Run verification in the foreground with explicit time caps (e.g. `timeout 900 make …`). Never end a turn while waiting on a background notification; the wake-up isn't reliable.
  - This also covers the reviewer hand-off from commit 5f14319: `artificer.md` step 3 and `code-reviewer.md` wait on report files with the Monitor tool, which is the same mechanism that failed here. Switch them to a foreground Bash until-loop with `timeout`, as `plan-reviewer.md` now does (the Bash tool caps a foreground call at 10 minutes, so repeat `timeout 540` loops rather than one `timeout 1800`).
- [ ] **Epic notes (`Ledger:`, `Smoke:`) go only in the main checkout**, the project branch at the repo root (`tk add-note` run there, then commit and push). Writing them in a stream worktree commits `.tickets/` changes on the stream branch, which conflicts at merge time. This happened in three of the four streams.
- [ ] **Squash-merge rebase rule for stacks.** When the parent PR squash-merges, rebase the child with `git rebase --onto <new-base> <old-parent-ref>`. If the parent was itself rebased before it was squashed, `<old-parent-ref>` must be the child's **original fork commit** (from `git merge-base` taken before the parent moved, or from the reflog), not the parent's final head. Otherwise the rebase replays the parent's pre-squash commits and conflicts. The digest stream hit this and recovered by using fork commit 5bc8291.
- [ ] Possibly: an artificer that finishes a stream should report once and stop. The digest artificer sent a duplicate idle report after its work was done.

### `verify-full` tier

- [ ] **Recipe for granting notification permission on the leased sim.** Notification permission and device-token registration never worked on the leased simulator, so push banner, tap routing and the settings selector were never observed on a sim and became Smoke notes. Find a recipe (e.g. `xcrun simctl privacy <udid> grant notifications <bundle-id>`, plus `xcrun simctl push` with an `.apns` payload for banner and tap tests), then add it to the verify-full guidance. That guidance likely lives in platform `docs/runbooks/worktree-verification.md`, with a pointer from artificer.md.

### Not now

- FIFO queue for the sim lease. Lease slots plus prompt release plus foreman nudges should be enough; revisit only if contention persists.

## Calibration round 2

- [ ] Fold the items above into the calibration round for the plan-reviewer and code-reviewer (see the platform memory note `project_process_upgrades`, pilot epic `pla-nl2e`), or land them first. Decide which.

## Hunk: ledger-focused view for the project->main review

Goal: on the big project->main merges, open Hunk showing only the files the Ledger flags, so the large unflagged files stay out of the way. The Hunk skills are in `skills/hunk-review/` and `skills/hunk-extensions/` (not yet committed).

- [ ] **Step 1, no new code: end the review with a filtered reload.** After writing the Ledger lines, the code-reviewer (or whoever runs the project->main pass) reloads the open Hunk session with git pathspecs. It lists the Ledger files, or excludes the noise:
  ```bash
  hunk session reload --repo . -- diff main...HEAD -- <ledger files...>
  hunk session reload --repo . -- diff main...HEAD -- . ':!**/*.lock' ':!path/to/generated'
  ```
  Limitations: excluded files leave the session entirely, with no toggle to bring them back (reload again without the pathspec), and it needs a live session (`hunk session list`). Not yet tried with `:!` exclusions, so check that Hunk passes them through to git. Also decide where it lives: a step in `agents/code-reviewer.md` Output, or in the final project->main review step instead.
- [ ] **Step 2, if step 1 proves useful: a small Hunk extension driven by the Ledger.** The reviewer writes a focus file (e.g. `.review/focus.json`: path, severity, reason per Ledger item). The extension's `hunk.transformChangeset` reads it and puts the Ledger files first, labelled with their severity (`[H] auth.ts`), and hides the rest behind a key that brings them back. It reloads when the file changes (`ctx.review.requestReload()`). Build it with the `hunk-extensions` skill. That keeps unflagged files one key away instead of gone.
- Not this: writing "read" entries into hunk-mark-read's state (`~/.local/state/hunk-mark-read/sessions/*.jsonl`). Its keys include a hash of each file's diff under the extension's own normalisation rules, which is fragile to copy.

## Dev process: move to herdr + ttt + hunk

- [ ] **Pass over the dev process for the new tooling stack.** I'm moving from sigil + nvim + tmux to herdr + ttt + hunk. Go through the files that encode the dev process and rewrite them for the new stack: which tool does each job (diff review, plan/doc review, panes and agent sessions), and how agents hand work to me in it. Sigil is archived (`archive/skills/sigil/`) and plannotator-tui now does plan/doc review. What's left is diff review: the artificer used to write sigil's `.sigil/review-order.yaml` (a suggested reading order with a note per file) at PR creation, and that was dropped with sigil; decide whether hunk gets an equivalent. Then commit `skills/hunk-review/` and `skills/hunk-extensions/`.

## Code review: borrow from ponytail

[ponytail](https://github.com/dietrichgebert/ponytail) is installed for hand use (`/ponytail-review`, `/ponytail-audit`, `/ponytail-debt`), with its always-on mode off via `dot-config/ponytail/config.json`. It doesn't replace `agents/code-reviewer.md`: it has no run-dir hand-off, findings JSON, Ledger notes, `INTERRUPT:`, dry-run or tiers, and none of the Penny-specific lenses.

- [ ] **Fold ponytail's review techniques into the code-reviewer and `shared/review-lenses/LENSES.md`.** Each fixes a gap in ours:
  - Grep every caller of a changed signature, return value or behaviour, including files outside the diff. Deep-tier lens passes read only around the changed lines, so a renamed field that breaks an untouched handler gets through.
  - Require a concrete failing case per finding ("this input leads to this wrong result"). The judge's verify step only confirms the quoted code exists.
  - Add a one-line "if we skip it" consequence per finding, to justify L/M/H and help James decide `needs-james` items.
  - State the load assumed; end with a "Not checked:" line.
  - A new lens for what no lens covers today: holds under load (check-then-write races, a query per item, lists that only grow), big slowdowns, and code that shouldn't exist (dead code, unused options, one-implementation abstractions).
  - `shortcut: <limit>, <when to upgrade>` comments count as recorded decisions, not findings. Consider surfacing `/ponytail-debt` next to the Ledger at the project->main PR.
  - LENSES.md is shared with the plan-reviewer, so check the new lens's "Applies when" for plans too. Fold in the other code-reviewer items in this file where they fit (the Monitor wait, calibration round 2, the Hunk filtered reload).

## Epic skill: make it project-agnostic

Found while ticketing Hearth's epic 1 (2026-11-02). `skills/epic/SKILL.md` still carries the platform project's assumptions, so a different repo has to redefine them inside each epic body.

- [ ] **Read verify tiers from the project.** The tier names (`verify-cursory`, `-integration`, `-full`, `-voice`) can stay, but their meanings are platform-specific: `make check`, the Compose stack with per-worktree ports and `INTEGRATION=1`, the iOS sim lease, ElevenLabs. Have the skill read each project's meanings from a "Verify tiers" section in its `CLAUDE.md` or `AGENTS.md`, and say what to do when a project doesn't define them. `agents/artificer.md` reads the same tiers, so update it to match.
- [ ] **Generalise the migrations rules.** "Apply once to the shared Supabase", `db reset` and `supabase/seed.sql` assume one shared hosted database. Reword them around the project's own schema setup (Hearth's is a local SQLite file whose migrations the adapter applies itself), with the Supabase specifics moving to the platform repo's docs.
- [ ] **Move the platform examples out.** The human-blocker examples (EL agent client events, ASC, `fly secrets set`, TestFlight) and the "Dry-run check" section (`pla-ha6d`, `pla-5c1f`) are platform tickets. Swap them for generic examples, or move them to a platform reference file the skill links to.
- [ ] Check `scripts/foreman.sh` and `resources/EPIC_TEMPLATE.md` for the same assumptions (the sim-lease slot lines in foreman, for example).
