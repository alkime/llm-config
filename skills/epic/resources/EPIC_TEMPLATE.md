# Epic body template

Copy, fill, pass via `tk create ... -d "$(cat file)"`. Delete sections only by writing the explicit "None" form.

```markdown
<One paragraph: goal and why now.> Plan: <path>. Vault: <note>.

Project branch `<project-branch>` (cut from main, pushed -u to its own remote). Stream PRs target it (or their stack parent). One PR to main at the end.

## Decisions
- <decision and why>

## Work Streams

### <stream-name> (branch: <branch>, base: <project-branch | stack parent>, size: S|M|L)
<task-id> <title> [verify-x] -> <task-id> <title> [verify-x]
after: <stream or task id>   (omit if independent)

## Stacks
None - all streams are siblings off the project branch.
<!-- or -->
main <- <external-parent-pr-branch> <- <project-branch>   (external; manage with `gh stack`)
<parent-branch> <- <child-branch>   (child PR targets parent; retarget + rebase --force-with-lease when parent merges)
Foundation PRs (HIGH findings interrupt): <branches>

## Migrations
Foundation task: <id>. Additive mid-project migrations: artificer may apply. Rewrites of applied migrations: human-blocker "schema rewind".
<!-- or --> No schema changes.

## Smoke-test guide (seed)
- [ ] <step James runs on the project->main PR, with expected result>
- [ ] (voice) <steps from verify-voice tasks>

## Before merging to main
- <human-blocker task id>: <what>

## Out of scope
- <item>
```

Ledger notes are appended later with `tk add-note <epic> "Ledger: ..."`; see the `pr` skill's LEDGER.md for the format.
