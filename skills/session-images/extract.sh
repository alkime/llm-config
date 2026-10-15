#!/bin/zsh
# Decode the images pasted into a Claude Code session and open them in Preview.
# usage: extract.sh [session-id | path/to/session.jsonl] [--no-open]
# With no session given, uses the current session ($CLAUDE_CODE_SESSION_ID).
set -e
open_them=1; arg=
for a in "$@"; do [[ $a == --no-open ]] && open_them=0 || arg=$a; done
arg=${arg:-$CLAUDE_CODE_SESSION_ID}
[[ -z $arg ]] && { echo "usage: $0 [session-id | session.jsonl] [--no-open]" >&2; exit 1; }

if [[ -f $arg ]]; then f=$arg
else f=$(find ~/.claude/projects -maxdepth 2 -name "$arg.jsonl" | head -1)
fi
[[ -z $f ]] && { echo "no transcript found for session $arg" >&2; exit 1; }

out=/tmp/claude-images/$(basename $f .jsonl)
rm -rf $out; mkdir -p $out; i=0
# Pasted images are top-level image blocks in user messages. Tool screenshots sit
# inside tool_result blocks and are skipped.
jq -r 'select(.type=="user" and (.isMeta|not)) | .message.content
       | if type=="array" then .[] else empty end
       | select(.type=="image") | "\(.source.media_type) \(.source.data)"' "$f" |
while read mt data; do
  i=$((i+1)); print -rn -- $data | base64 -d > $out/$(printf %02d $i).${mt#image/}
done

echo "$i image(s) -> $out"
(( i > 0 && open_them )) && open $out/*
exit 0
