# llm-config

James's Claude Code configuration, plus the configs of the terminal tools around it (herdr, plannotator-tui, ttt). `agents/`, `commands/`, `skills/`, `shared/` and `claude-global-settings.json` (as `settings.json`) are symlinked into `~/.claude`, and the files under `dot-config/` into `~/.config`, so edits here go live immediately. `install.sh` creates the links; it is safe to re-run.

## Layout

- `agents/`: the hands-off pipeline agents: `artificer`, `code-reviewer`, `plan-reviewer`.
- `skills/`: user skills (`epic`, `pr`, `sigil`, `ios-sim`, …). `skills/synced/` is written by Claude Code itself (it syncs James's claude.ai account skills here, because `~/.claude/skills` points into this repo); don't hand-edit it. `skills/herdr/SKILL.md` is vendored from `herdr --skill` (matched to the installed binary); after upgrading herdr, regenerate it with `herdr --skill > skills/herdr/SKILL.md` rather than editing it.
- `shared/review-lenses/LENSES.md`: the lens catalog shared by both reviewers.
- `commands/`: slash commands.
- `archive/`: retired agents and skills, kept for reference.
- `dot-config/`: a tracked subset of `~/.config`, linked file by file (`dot-config/herdr/config.toml` → `~/.config/herdr/config.toml`). The rest of those directories is the tools' own state (sockets, logs, sessions, plugin checkouts) and stays out of the repo. To track another file, move it here and re-run `install.sh`. herdr plugins aren't tracked as files; reinstall them with `herdr plugin install plannotator/herdr-annotate` and `herdr plugin install eugenioenko/ttt/herdr-plugin`.
- `scripts/`: helpers, e.g. `claude-plan-review` (herdr `prefix+i`: opens the focused Claude session's plan in plannotator-tui).

## TODO.md

`TODO.md` is the running list of pending changes to the design, planning and verification agents and their supporting files. Several sessions add to it.

- When a session finds a change worth making here but isn't making it now, add an item to the right section of `TODO.md`. Name the failure it fixes.
- Before changing an agent, skill or shared file, check `TODO.md` for items about it and fold them in where they fit.
- When an item lands, delete it from `TODO.md` in the same commit. Git history keeps the record.
