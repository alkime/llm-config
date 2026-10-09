#!/usr/bin/env bash
# sim-say.sh — speak text into the iOS Simulator's microphone.
#
# Temporarily switches the Mac's default audio input to BlackHole, plays the
# text into BlackHole with `say`, then restores the previous input — always,
# via an EXIT trap, so a failed or interrupted run never leaves the Mac's mic
# hijacked. The Simulator must be on I/O → Audio Input → System (the default)
# so it follows the Mac's default input.
#
# The app opens its recorder on whatever input is current when recording
# starts, so pass the "start recording" action via --start: it runs after the
# switch to BlackHole and before speaking.
#
# Usage: sim-say.sh [--start "<cmd>"] [--pre <secs>] [-v <voice>] "text to speak"
#   e.g. sim-say.sh --start "axe tap -x 201 -y 539 --udid $U" "Remind me to call George"
# Requires: brew install blackhole-2ch switchaudio-osx
set -euo pipefail

DEVICE="BlackHole 2ch"
VOICE=""
START=""
PRE="1.5"   # settle time after --start (or the switch), before speaking

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v) VOICE="$2"; shift 2 ;;
    --pre) PRE="$2"; shift 2 ;;
    --start) START="$2"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) break ;;
  esac
done
[[ $# -ge 1 ]] || { echo "usage: $0 [-v voice] [--pre secs] \"text\"" >&2; exit 2; }
TEXT="$*"

command -v SwitchAudioSource >/dev/null || { echo "missing: brew install switchaudio-osx" >&2; exit 1; }
SwitchAudioSource -a -t input | grep -qx "$DEVICE" || { echo "missing input device: $DEVICE" >&2; exit 1; }

PREV=$(SwitchAudioSource -c -t input)
restore() { SwitchAudioSource -t input -s "$PREV" >/dev/null; }
trap restore EXIT

SwitchAudioSource -t input -s "$DEVICE" >/dev/null
sleep 0.3
[[ -n "$START" ]] && bash -c "$START"
sleep "$PRE"
if [[ -n "$VOICE" ]]; then
  say -a "$DEVICE" -v "$VOICE" "$TEXT"
else
  say -a "$DEVICE" "$TEXT"
fi
sleep 0.3   # let the tail of the utterance reach the recorder
echo "spoke via $DEVICE; input restored to: $PREV" >&2
