# llm-config

James's Claude Code configuration. `agents/`, `commands/`, `skills/`, `shared/` and `claude-global-settings.json` (as `settings.json`) are symlinked into `~/.claude`, so edits here go live in every session immediately.

## Layout

- `agents/`: the hands-off pipeline agents: `artificer`, `code-reviewer`, `plan-reviewer`.
- `skills/`: user skills (`epic`, `pr`, `sigil`, `ios-sim`, …). `skills/synced/` is written by Claude Code itself (it syncs James's claude.ai account skills here, because `~/.claude/skills` points into this repo); don't hand-edit it.
- `shared/review-lenses/LENSES.md`: the lens catalog shared by both reviewers.
- `commands/`: slash commands.
- `archive/`: retired agents and skills, kept for reference.

## TODO.md

`TODO.md` is the running list of pending changes to the design, planning and verification agents and their supporting files. Several sessions add to it.

- When a session finds a change worth making here but isn't making it now, add an item to the right section of `TODO.md`. Name the failure it fixes.
- Before changing an agent, skill or shared file, check `TODO.md` for items about it and fold them in where they fit.
- When an item lands, delete it from `TODO.md` in the same commit. Git history keeps the record.
