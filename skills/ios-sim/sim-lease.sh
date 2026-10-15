#!/usr/bin/env bash
# sim-lease.sh — exclusive leases on dedicated agent iOS simulators.
#
# Agents running simulator smoke tests from worktrees must not touch the
# simulator a human has booted. This script owns a small pool of separate
# simulators ("Agent Sim 1", "Agent Sim 2", …, created on first use) with one
# lock per slot, so each slot is driven by one worktree at a time. It never
# boots, shuts down or erases any other simulator.
#
# Simulators are machine-wide, so the lease is too: every project on this
# machine shares the same pool. Lives in llm-config (~/.claude/skills/ios-sim/);
# projects call it directly or through a one-line wrapper.
#
# Usage:
#   sim-lease.sh acquire [--wait SECS] [--pid PID]   # prints the UDID
#   sim-lease.sh release [--slot N --force] [--keep-booted]
#   sim-lease.sh status                              # one line per slot
#
# Typical use from a worktree:
#   export SIM_UDID="$(~/.claude/skills/ios-sim/sim-lease.sh acquire)"   # fails fast if all held
#   ... make e2e-mobile / ios-sim smoke with SIM_UDID ...
#   ~/.claude/skills/ios-sim/sim-lease.sh release
#
# acquire reuses the slot this worktree already holds, else takes the first
# free (or stale) slot. A lease is stale (and taken over) when --pid was given
# and that process is gone, or when it is older than SIM_LEASE_MAX_AGE seconds
# (default 3600). Exit status 75 means every slot is held by someone else (the
# holders are printed on stderr).
#
# Environment:
#   SIM_LEASE_SLOTS    number of slots, 1–4 (default 2)
#   SIM_LEASE_DIR      lock root (default ~/.cache/claude-sim-lease)
#   SIM_LEASE_MAX_AGE  stale threshold in seconds (default 3600)
#   AGENT_SIM_PREFIX   simulator name prefix (default "Agent Sim"; slot N is "<prefix> N")

set -euo pipefail

AGENT_SIM_PREFIX="${AGENT_SIM_PREFIX:-Agent Sim}"
LEASE_ROOT="${SIM_LEASE_DIR:-$HOME/.cache/claude-sim-lease}"
MAX_AGE="${SIM_LEASE_MAX_AGE:-3600}"
SLOTS="${SIM_LEASE_SLOTS:-2}"
MAX_SLOTS=4
EX_HELD=75

die() { echo "sim-lease: $*" >&2; exit 1; }

[[ "$SLOTS" =~ ^[0-9]+$ ]] && (( SLOTS >= 1 && SLOTS <= MAX_SLOTS )) ||
  die "SIM_LEASE_SLOTS must be 1–$MAX_SLOTS (got '$SLOTS')"

mkdir -p "$LEASE_ROOT"

command -v xcrun >/dev/null 2>&1 || die "xcrun not found — Xcode + Command Line Tools required"

here="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

lock_dir() { echo "$LEASE_ROOT/lock-$1"; } # mkdir is atomic: the directory IS the lock
sim_name() { echo "$AGENT_SIM_PREFIX $1"; }

# field SLOT KEY: read KEY from the slot's owner file.
field() { sed -n "s/^$2=//p" "$(lock_dir "$1")/owner" 2>/dev/null | head -1; }

now() { date +%s; }

is_stale() {
  local lock pid since
  lock="$(lock_dir "$1")"
  [[ -d "$lock" ]] || return 1
  pid="$(field "$1" pid)"
  since="$(field "$1" since)"
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then return 0; fi
  if [[ -z "$since" ]]; then
    # Lock dir exists but the owner file isn't written yet: a holder mid-acquire.
    (( $(now) - $(stat -f %m "$lock") > 30 )) && return 0
    return 1
  fi
  if (( $(now) - since > MAX_AGE )); then return 0; fi
  return 1
}

describe_holder() {
  local since age
  since="$(field "$1" since)"
  age=$(( $(now) - ${since:-$(now)} ))
  echo "held by worktree '$(field "$1" worktree)' (pid '$(field "$1" pid)') for ${age}s since $(field "$1" since_human)"
}

# The slot this worktree holds, if any.
own_slot() {
  local s
  for (( s = 1; s <= SLOTS; s++ )); do
    if [[ -d "$(lock_dir "$s")" && "$(field "$s" worktree)" == "$here" ]]; then
      echo "$s"
      return 0
    fi
  done
  return 1
}

# Print the UDID of the named agent simulator, creating it if needed.
agent_udid() {
  local name="$1" udid
  udid="$(xcrun simctl list devices -j | python3 -c '
import json, sys
name = sys.argv[1]
for runtime, devices in json.load(sys.stdin)["devices"].items():
    for d in devices:
        if d["name"] == name and d.get("isAvailable", True):
            print(d["udid"]); sys.exit(0)' "$name")"
  if [[ -n "$udid" ]]; then echo "$udid"; return; fi

  # Create one: newest available iOS runtime x newest base iPhone device type.
  local spec devtype runtime
  spec="$(python3 - <<'PY'
import json, re, subprocess, sys
rt = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "runtimes", "-j"]))["runtimes"]
rt = [r for r in rt if r.get("isAvailable", True) and r["identifier"].startswith("com.apple.CoreSimulator.SimRuntime.iOS")]
if not rt:
    sys.exit("no iOS runtime installed")
def ver(r): return tuple(int(x) for x in re.findall(r"\d+", r["version"]))
runtime = max(rt, key=ver)
dts = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devicetypes", "-j"]))["devicetypes"]
supported = {d["identifier"] for d in runtime.get("supportedDeviceTypes", [])}
cands = []
for d in dts:
    m = re.fullmatch(r"iPhone (\d+)", d["name"])  # base models only
    if m and d["identifier"] in supported:
        cands.append((int(m.group(1)), d["identifier"]))
if not cands:
    sys.exit("no base iPhone device type for runtime " + runtime["identifier"])
print(max(cands)[1], runtime["identifier"])
PY
)" || die "cannot pick a device type/runtime for the agent simulator"
  devtype="${spec%% *}"
  runtime="${spec##* }"
  echo "sim-lease: creating simulator '$name' ($devtype, $runtime)" >&2
  xcrun simctl create "$name" "$devtype" "$runtime"
}

boot() {
  # Boot only our own simulator; "Unable to boot ... current state: Booted" is fine.
  xcrun simctl boot "$1" 2>/dev/null || true
  xcrun simctl bootstatus "$1" -b >&2
}

cmd_acquire() {
  local wait_secs=0 pid="" deadline
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --wait) wait_secs="$2"; shift 2 ;;
      --pid) pid="$2"; shift 2 ;;
      *) die "unknown flag: $1" ;;
    esac
  done
  deadline=$(( $(now) + wait_secs ))

  local slot="" s lock udid
  if slot="$(own_slot)"; then
    udid="$(field "$slot" udid)"
    if [[ -n "$udid" ]]; then
      # Keep the recorded owner file as is; just make sure the sim is up.
      echo "sim-lease: slot $slot already held by this worktree — reusing" >&2
      boot "$udid"
      echo "$udid"
      return 0
    fi
    # Our own half-written lease (an interrupted acquire): finish it below.
  fi

  while [[ -z "$slot" ]]; do
    for (( s = 1; s <= SLOTS; s++ )); do
      lock="$(lock_dir "$s")"
      if [[ -d "$lock" ]] && is_stale "$s"; then
        # Atomic takeover: rename the stale lock away. Of several racers only
        # one mv succeeds; the rest simply retry the mkdir below.
        local stale="$lock.stale.$$"
        if mv "$lock" "$stale" 2>/dev/null; then
          echo "sim-lease: took over stale lease on slot $s" >&2
          rm -rf "$stale"
        fi
      fi
      if mkdir "$lock" 2>/dev/null; then slot="$s"; break; fi
    done
    [[ -n "$slot" ]] && break
    if (( $(now) >= deadline )); then
      echo "sim-lease: all $SLOTS agent simulator slots are held:" >&2
      for (( s = 1; s <= SLOTS; s++ )); do echo "  slot $s: $(describe_holder "$s")" >&2; done
      exit "$EX_HELD"
    fi
    sleep 5
  done

  lock="$(lock_dir "$slot")"
  {
    echo "slot=$slot"
    echo "worktree=$here"
    echo "pid=$pid"
    echo "since=$(now)"
    echo "since_human=$(date '+%Y-%m-%d %H:%M:%S')"
  } >"$lock/owner"

  # From here until success, any failure or interruption must not leave an
  # orphaned lock behind.
  trap 'rm -rf "$lock"' EXIT
  trap 'rm -rf "$lock"; exit 1' INT TERM

  udid="$(agent_udid "$(sim_name "$slot")")"
  boot "$udid"
  echo "udid=$udid" >>"$lock/owner"
  trap - EXIT INT TERM
  echo "sim-lease: holding slot $slot ($(sim_name "$slot"))" >&2
  echo "$udid"
}

cmd_release() {
  local force=false keep=false slot=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force) force=true; shift ;;
      --keep-booted) keep=true; shift ;;
      --slot) slot="$2"; shift 2 ;;
      *) die "unknown flag: $1" ;;
    esac
  done

  if [[ -z "$slot" ]]; then
    if ! slot="$(own_slot)"; then
      echo "sim-lease: this worktree holds no slot" >&2
      return 0
    fi
  else
    [[ "$slot" =~ ^[0-9]+$ ]] && (( slot >= 1 && slot <= SLOTS )) || die "--slot must be 1–$SLOTS"
    if [[ ! -d "$(lock_dir "$slot")" ]]; then echo "sim-lease: slot $slot not held" >&2; return 0; fi
    if [[ "$(field "$slot" worktree)" != "$here" && "$force" == false ]] && ! is_stale "$slot"; then
      echo "sim-lease: slot $slot is $(describe_holder "$slot"); pass --force to release it anyway" >&2
      exit "$EX_HELD"
    fi
  fi

  local udid
  udid="$(field "$slot" udid)"
  rm -rf "$(lock_dir "$slot")"
  # Only ever shut down the agent simulator recorded in the lease.
  if [[ "$keep" == false && -n "$udid" ]]; then
    xcrun simctl shutdown "$udid" 2>/dev/null || true
  fi
  echo "sim-lease: released slot $slot" >&2
}

cmd_status() {
  local s
  for (( s = 1; s <= SLOTS; s++ )); do
    if [[ ! -d "$(lock_dir "$s")" ]]; then
      echo "slot $s: free"
    elif is_stale "$s"; then
      echo "slot $s: stale ($(describe_holder "$s"))"
    else
      echo "slot $s: $(describe_holder "$s"), udid $(field "$s" udid)"
    fi
  done
}

sub="${1:-}"
[[ -n "$sub" ]] || die "usage: sim-lease.sh acquire|release|status"
shift
case "$sub" in
  acquire) cmd_acquire "$@" ;;
  release) cmd_release "$@" ;;
  status) cmd_status ;;
  *) die "unknown command: $sub" ;;
esac
