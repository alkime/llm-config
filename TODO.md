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
