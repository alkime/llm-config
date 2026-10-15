---
name: session-images
description: Pull the screenshots James pasted into a Claude Code session out of its transcript as image files and open them in Preview. Use when James asks to see, save, open or find the images or screenshots he attached to this or an earlier session.
---

# Session images

Claude Code never writes pasted images to disk as files. They live base64-encoded inside the session transcript, `~/.claude/projects/<project-dir>/<session-id>.jsonl`. `extract.sh` decodes them.

```zsh
~/.claude/skills/session-images/extract.sh                 # current session
~/.claude/skills/session-images/extract.sh <session-id>    # another session
~/.claude/skills/session-images/extract.sh <file>.jsonl --no-open
```

Images land in `/tmp/claude-images/<session-id>/` as `01.png`, `02.jpeg`, … in paste order (the folder is cleared first), and open in Preview unless `--no-open` is passed. Report the folder path back.

Only pasted images are extracted. Screenshots taken by tools (Playwright, simulator) sit inside tool results and are skipped.

To find an earlier session that had pasted images, `grep -l '"type":"image"' ~/.claude/projects/*/*.jsonl` (this also matches sessions with only tool screenshots), or ask James for the session id (`/status` shows it).
