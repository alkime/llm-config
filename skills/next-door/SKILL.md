---
name: next-door
description: Run commands in the terminal pane next to this Claude session in herdr, where James can watch them. Use when James says "next-door pane", "the pane next door", "neighbouring pane", "the other pane", "over there" or similar, e.g. "in the next-door pane, run the dev server" or "start the tests next door". Requires HERDR_ENV=1.
---

# Next-door pane

James keeps a shell pane beside his Claude pane in the same herdr tab. "The next-door pane" means that pane. Commands run there are visible to him, and long-running ones (dev servers, watchers, test runs) keep going after your turn ends. Use it when he asks; your own one-off commands still go through Bash.

## Find it

```zsh
~/.claude/skills/next-door/next-door          # pane ID, or exit 1 with the reason
~/.claude/skills/next-door/next-door --idle   # also require the shell to be at its prompt
```

It picks the pane in your tab labelled `next-door`, or else the only pane in the tab with no agent in it. If it finds none:

- **No other pane:** create one, label it so it's found next time, and keep focus here:
  ```zsh
  p=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | jq -r .result.pane.pane_id)
  herdr pane rename "$p" next-door
  ```
  Split `down` instead if this pane is narrow (see `herdr pane layout --pane "$HERDR_PANE_ID"`).
- **Several shell panes, none labelled:** ask James which one he means, then label it with `herdr pane rename <id> next-door`.

## Drive it

```zsh
herdr pane run "$nd" "just test"                                   # types the command and Enter
herdr pane wait-output "$nd" --match "test result" --timeout 120000
herdr pane read "$nd" --source recent-unwrapped --lines 120
```

- Check `--idle` before `pane run`. If something is running there, it is James's: say what is running (`herdr pane read`) and ask before sending Ctrl-C (`herdr pane send-keys "$nd" ctrl+c`) or typing over it. The exception is a process you started there this session.
- `pane run` reports that the command was queued, not that it finished. Wait on output you expect, and read the pane before reporting a result.
- Leave focus where it is unless James asks to look at the pane.
- Don't close the pane; it's his.

For anything beyond this (agents in panes, other tabs, waits on agent state), load the `herdr` skill.
