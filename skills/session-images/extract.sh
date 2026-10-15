#!/bin/zsh
# Decode the images pasted into a Claude Code session and list them.
# usage: extract.sh [session-id | path/to/session.jsonl] [--open [N ...]]
# With no session given, uses the current session ($CLAUDE_CODE_SESSION_ID).
# --open alone opens every image in Preview; --open 2 5 opens just those.
set -e
arg=; opening=0; picks=()
for a in "$@"; do
  if [[ $a == --open ]]; then opening=1
  elif (( opening )) && [[ $a == <-> ]]; then picks+=($a)
  else arg=$a
  fi
done
arg=${arg:-$CLAUDE_CODE_SESSION_ID}
[[ -z $arg ]] && { echo "usage: $0 [session-id | session.jsonl] [--open [N ...]]" >&2; exit 1; }

if [[ -f $arg ]]; then f=$arg
else f=$(find ~/.claude/projects -maxdepth 2 -name "$arg.jsonl" | head -1)
fi
[[ -z $f ]] && { echo "no transcript found for session $arg" >&2; exit 1; }

out=/tmp/claude-images/$(basename $f .jsonl)
rm -rf $out; mkdir -p $out; i=0
# Pasted images are top-level image blocks in user messages. Tool screenshots sit
# inside tool_result blocks and are skipped. Each line carries the message time and
# the start of the text pasted alongside, so the list says which image is which.
jq -r 'select(.type=="user" and (.isMeta|not)) | (.timestamp // "") as $ts
       | .message.content | if type=="array" then . else empty end
       | ([.[] | select(.type=="text") | .text] | join(" ") | gsub("\\s+";" ") | .[0:70]) as $txt
       | .[] | select(.type=="image")
       | [.source.media_type, .source.data, ($ts | .[0:16] | sub("T";" ")), $txt] | @tsv' "$f" |
while IFS=$'\t' read mt data ts txt; do
  i=$((i+1)); img=$out/$(printf %02d $i).${mt#image/}
  print -rn -- $data | base64 -d > $img
  size=$(sips -g pixelWidth -g pixelHeight $img 2>/dev/null | awk '/pixel/{print $2}' | paste -sd x -)
  printf '%2d  %s  %-10s  %s\n' $i "$ts" "$size" "${txt:-(no text)}"
done

echo "$i image(s) in $out"
if (( opening && i > 0 )); then
  if (( ${#picks} )); then for n in $picks; do open $out/$(printf %02d $n).*; done
  else open $out/*
  fi
fi
exit 0
