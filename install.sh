#!/usr/bin/env bash
# Symlink this repo into ~/.claude and ~/.config. Safe to re-run: correct
# links are left alone, and anything else in the way is moved to <path>.bak.
set -euo pipefail

repo=$(cd "$(dirname "$0")" && pwd)

link() {
  local src=$1 dst=$2
  if [[ -L $dst && $(readlink "$dst") == "$src" ]]; then
    return
  fi
  mkdir -p "$(dirname "$dst")"
  if [[ -e $dst || -L $dst ]]; then
    mv "$dst" "$dst.bak"
    echo "moved existing $dst to $dst.bak"
  fi
  ln -s "$src" "$dst"
  echo "linked $dst -> $src"
}

# Claude Code
for d in agents commands skills shared; do
  link "$repo/$d" ~/.claude/$d
done
link "$repo/claude-global-settings.json" ~/.claude/settings.json

# dot-config/ mirrors ~/.config, file by file.
while IFS= read -r f; do
  link "$repo/dot-config/$f" ~/.config/"$f"
done < <(cd "$repo/dot-config" && find . -type f ! -name .DS_Store | sed 's|^\./||')
