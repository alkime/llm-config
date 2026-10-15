# TODO

A running list of llm-config changes waiting to be made. Add new items at the bottom of their section. Delete an item once it lands; git history keeps the record.

## Pipeline: lessons from the Notifications Iteration run (2026-10-14/15)

Source: the first full epic run on the new pipeline (platform epics `pla-dfvy` and `pla-zv04`, 4 stream PRs #350–#353). Each item names the failure it fixes.

### Foreman monitoring (orchestrator side)

- [ ] **Make foreman monitoring a routine step in the `epic` skill**, or in a small companion section that covers launching artificers. Once the artificers launch, the orchestrator session runs a Monitor loop that polls:
  - who owns the sim lease and how old it is (`~/.cache/pennyhelps/sim-lease/lock/owner`);
  - each stream branch's head commit (`git ls-remote`);
  - each stream PR's state (`gh pr view --json state,mergedAt,baseRefName`).

  It nudges an artificer (SendMessage) when that artificer has held the lease for more than ~20m with no new commit, when its stream's head hasn't moved for ~45m, or when its stack parent merges (the child must rebase). It re-arms after every event and stops when every stream PR has merged.
  - **Why:** artificers' own background Monitor/wait calls didn't wake them. Circles held the lease for 67m and push-modes for 84m while everything sat idle until James asked "everything seems idle?".
  - Platform side (not this repo): a `scripts/foreman.sh <project-branch> <stream>…` that prints one status line per stream, so the Monitor command stays short. A one-line pointer in platform `AGENTS.md`, pipeline step 3.

### `agents/artificer.md`

- [ ] **No background waits at the end of a turn.** Run verification in the foreground with explicit time caps (e.g. `timeout 900 make …`). Never end a turn while waiting on a background notification; the wake-up isn't reliable.
- [ ] **Release the sim lease right after the sim step**, before code review, PR edits or anything else. The lease is shared by every stream.
- [ ] **Epic notes (`Ledger:`, `Smoke:`) go only in the main checkout**, the project branch at the repo root (`tk add-note` run there, then commit and push). Writing them in a stream worktree commits `.tickets/` changes on the stream branch, which conflicts at merge time. This happened in three of the four streams.
- [ ] **Squash-merge rebase rule for stacks.** When the parent PR squash-merges, rebase the child with `git rebase --onto <new-base> <old-parent-ref>`. If the parent was itself rebased before it was squashed, `<old-parent-ref>` must be the child's **original fork commit** (from `git merge-base` taken before the parent moved, or from the reflog), not the parent's final head. Otherwise the rebase replays the parent's pre-squash commits and conflicts. The digest stream hit this and recovered by using fork commit 5bc8291.
- [ ] Possibly: an artificer that finishes a stream should report once and stop. The digest artificer sent a duplicate idle report after its work was done.

### `verify-full` tier

- [ ] **Recipe for granting notification permission on the leased sim.** Notification permission and device-token registration never worked on the leased simulator, so push banner, tap routing and the settings selector were never observed on a sim and became Smoke notes. Find a recipe (e.g. `xcrun simctl privacy <udid> grant notifications <bundle-id>`, plus `xcrun simctl push` with an `.apns` payload for banner and tap tests), then add it to the verify-full guidance. That guidance likely lives in platform `docs/runbooks/worktree-verification.md`, with a pointer from artificer.md.

### Not now

- FIFO queue for the sim lease. A single lease plus prompt release plus foreman nudges should be enough; revisit only if contention persists.

## Calibration round 2

- [ ] Fold the items above into the calibration round for the plan-reviewer and code-reviewer (see the platform memory note `project_process_upgrades`, pilot epic `pla-nl2e`), or land them first. Decide which.
