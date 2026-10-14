# Ledger format and project->main PR mode

The Ledger is the set of review findings that artificers/code-reviewer could not simply fix and that James should see on the project->main PR. It lives as notes on the epic ticket (durable, ordered, no extra files).

## Writing (done by code-reviewer / artificers)

```bash
tk add-note <epic-id> "Ledger: PR#<n> | <file>:<line> | lens=<lens> | sev=<L|M|H> | <summary> | disp=<fixed|deferred|needs-james> | interrupt=<yes|no>"
```

Fields: PR number, `file:line`, lens name, severity (L/M/H), one-line summary, disposition, interrupt flag (set when a HIGH finding on a foundation PR interrupted James). Use `Smoke: <step>` notes to add steps to the smoke-test guide.

## Parsing (render_ledger.py) is tolerant by design

The format is owned by the code-reviewer agent; the renderer must not break if it drifts. Accepted:
- `|`-separated fields in any order, with or without `key=` prefixes (`sev=H`, `severity: high`, bare `[M]`/`H`).
- Free text: PR via `#13`/`PR 13`/`PR#13`, location via `path/file.ext:line`, severity via `[H]`, `HIGH`, `sev=M`, or a bare `L`, disposition via the words fixed/deferred/needs-james, interrupt via the word "interrupt".
- Several entries in one note as `- ` bullets or repeated `Ledger:` lines.
- Anything unparseable still renders (summary = raw text, severity "Unrated", disposition "unspecified"). Entries are never dropped.
- Non-ledger notes are ignored.

If code-reviewer's agent definition changes the format, update the examples here and add a case to the dry-run in the PR that changes it; the parser should keep accepting the old form.

## Project->main mode (pr:open)

Trigger: the base is `main` AND the head branch is the epic's project branch (named in the epic body's Work Streams/intro, or a branch that other open/merged PRs target). Steps:

1. Find the epic: `tk list -T epic` and match the project branch name in the epic body, or take the id from the user. Ask if ambiguous.
2. Render: `python3 ${CLAUDE_SKILL_DIR}/bin/render_ledger.py <epic-id> > /tmp/claude/ledger.md` (run from the repo that owns the tickets).
3. Compose the body: Summary (streams merged, from `gh pr list --state merged --base <project-branch>`), then the rendered `## Ledger` and `## Smoke-test guide`, then `## Before merging` (the e2e attestation reminder: James runs `make e2e` from the main checkout on this branch; open human-blocker tasks).
4. Lead with Ledger items whose disposition is `needs-james`. An empty Ledger is stated explicitly ("No flagged review items.").
5. `gh pr create --base main` / `gh pr edit --body-file`. Re-run and `gh pr edit` whenever new Ledger notes land; the body is regenerated, not hand-edited.

Voice (`verify-voice`) tasks and simulator (`verify-full`) tasks are listed automatically as smoke items from task tags; seed steps come from the epic's `## Smoke-test guide (seed)` section.
