---
name: session-images
description: Pull the screenshots James pasted into a Claude Code session out of its transcript as image files, list them, and open the ones he wants in Preview. Use when James asks to see, save, open or find the images or screenshots he attached to this or an earlier session.
---

# Session images

Claude Code also saves pasted images as `/private/tmp/claude-501/<project-dir>/<session-id>/images/<n>.png` (the path appears in the message). That copy is in `/tmp` and is gone after a reboot. The lasting copy is base64-encoded inside the session transcript, `~/.claude/projects/<project-dir>/<session-id>.jsonl`, and `extract.sh` decodes it, so it works for any session.

```zsh
~/.claude/skills/session-images/extract.sh                 # current session
~/.claude/skills/session-images/extract.sh <session-id>    # another session
~/.claude/skills/session-images/extract.sh --open 2 5      # also open images 2 and 5 in Preview
~/.claude/skills/session-images/extract.sh --open          # open them all
```

Images land in `/tmp/claude-images/<session-id>/` as `01.png`, `02.jpeg`, … in paste order (the folder is cleared first). The script prints one line per image: number, time (UTC), dimensions, and the start of the text pasted with it. Show James that list and ask which to open, unless he already said; don't open them all by default.

Only pasted images are extracted. Screenshots taken by tools (Playwright, simulator) sit inside tool results and are skipped.

To find an earlier session that had pasted images, `grep -l '"type":"image"' ~/.claude/projects/*/*.jsonl` (this also matches sessions with only tool screenshots), or ask James for the session id (`/status` shows it).
