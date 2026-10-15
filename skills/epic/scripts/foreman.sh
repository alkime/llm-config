#!/usr/bin/env bash
# foreman.sh — one status snapshot of an epic's streams, for the orchestrator's
# Monitor loop (see the epic skill, "Launch and supervise artificers").
#
# Usage (from the project's main checkout):
#   foreman.sh <project-branch> <stream-branch>…
#
# Prints one line per stream, then the sim-lease slots. Lines that need the
# orchestrator's attention start with "!":
#   ! STALLED   stream head hasn't moved for FOREMAN_STALL_MIN minutes (default 45)
#   ! REBASE    the stream's PR base is a stack parent whose PR has merged
#   ! LEASE     a sim slot held for more than FOREMAN_LEASE_MIN minutes (default 20)
# The last line is "ALL MERGED" once every stream PR has merged, else "RUNNING".
# Exit status is always 0 unless the arguments are wrong.

set -euo pipefail

STALL_MIN="${FOREMAN_STALL_MIN:-45}"
LEASE_MIN="${FOREMAN_LEASE_MIN:-20}"
SIM_LEASE="${SIM_LEASE:-$HOME/.claude/skills/ios-sim/sim-lease.sh}"

[[ $# -ge 2 ]] || { echo "usage: foreman.sh <project-branch> <stream-branch>…" >&2; exit 2; }
project="$1"; shift
streams=("$@")

now="$(date +%s)"
# One fetch per branch: a single fetch fails as a whole if any branch is missing.
for b in "$project" "${streams[@]}"; do git fetch -q origin "$b" 2>/dev/null || true; done

# PR fields per branch: state, base, number (the most recent PR for that head).
pr_info() {
  gh pr list --head "$1" --state all --limit 1 \
    --json number,state,baseRefName --jq '.[0] // empty | "\(.number) \(.state) \(.baseRefName)"' 2>/dev/null || true
}

# Parallel arrays indexed like $streams (macOS ships bash 3.2: no associative arrays).
pr_num=(); pr_state=(); pr_base=()
for i in "${!streams[@]}"; do
  num="" st="" base=""
  read -r num st base <<<"$(pr_info "${streams[$i]}")" || true
  pr_num[$i]="$num"; pr_state[$i]="${st:-NONE}"; pr_base[$i]="$base"
done

# PR state of a branch if it is one of the streams, else empty.
state_of() {
  local i
  for i in "${!streams[@]}"; do
    [[ "${streams[$i]}" == "$1" ]] && { echo "${pr_state[$i]}"; return; }
  done
}

all_merged=true
for i in "${!streams[@]}"; do
  b="${streams[$i]}"
  st="${pr_state[$i]}"
  [[ "$st" == MERGED ]] || all_merged=false

  if sha_ct="$(git log -1 --format='%h %ct' "origin/$b" 2>/dev/null)"; then
    sha="${sha_ct% *}"; age=$(( (now - ${sha_ct#* }) / 60 ))
    head="head $sha (${age}m ago)"
  else
    sha=""; age=0; head="no remote branch"
  fi

  pr="no PR"
  base="${pr_base[$i]}"
  [[ -n "${pr_num[$i]}" ]] && pr="PR #${pr_num[$i]} $st base=$base"

  flag=""
  if [[ "$st" == OPEN && -n "$base" && "$base" != "$project" && "$(state_of "$base")" == MERGED ]]; then
    flag="! REBASE  "
  elif [[ "$st" != MERGED && -n "$sha" ]] && (( age >= STALL_MIN )); then
    flag="! STALLED "
  fi
  echo "${flag}$b: $head, $pr"
done

if [[ -x "$SIM_LEASE" ]]; then
  while IFS= read -r line; do
    # "slot N: held by worktree '…' (pid '…') for 1234s since …"
    if [[ "$line" =~ for\ ([0-9]+)s\ since ]] && (( BASH_REMATCH[1] / 60 >= LEASE_MIN )); then
      echo "! LEASE   sim $line"
    else
      echo "sim $line"
    fi
  done < <("$SIM_LEASE" status 2>/dev/null || true)
fi

$all_merged && echo "ALL MERGED" || echo "RUNNING"
