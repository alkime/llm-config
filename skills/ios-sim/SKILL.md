---
name: ios-sim
description: Drive the iOS Simulator from the CLI — launch apps, tap/type/swipe, read the UI accessibility tree, capture screenshots, set permissions/location/deep-links. Use when the user wants to interact with an iOS app on the Simulator, take simulator screenshots, automate or test a Flutter/iOS app's UI, or reproduce a flow on the booted simulator. The iOS analog of playwright-cli.
---

# iOS Simulator automation with AXe + simctl

Two tools, used together:

- **`axe`** ([cameroncooke/AXe](https://github.com/cameroncooke/AXe), MIT, Homebrew:
  `brew install cameroncooke/axe/axe`) — the interaction layer: **read the accessibility
  tree, tap, type, swipe, gestures, hardware buttons, batch flows, screenshots, video**.
  Injects HID events straight into the simulator, so it works **with the Simulator
  window in the background** — no focus juggling. Verified on Xcode 26.3 / iOS 26.3.
- **`xcrun simctl`** — Apple-native: boot, install/launch apps, deep links,
  permissions, push, status bar, location.

(Replaces SimPilot, which needed the window frontmost, crashed on screenshots, and has
been unmaintained since 2026-03.)

## Critical: always pass the booted UDID

Every `axe` command requires `--udid`. Resolve it once:

```bash
U=$(xcrun simctl list devices booted -j | python3 -c 'import json,sys;d=json.load(sys.stdin)["devices"];print(next((x["udid"] for v in d.values() for x in v),""))')
echo "$U"   # empty → nothing booted
```

Nothing booted? In the Penny repo, `./scripts/ensure-simulator.sh` boots the standard
e2e device (iPhone 17, iOS 26.3). Otherwise `xcrun simctl boot "<name>"`.

## Reading the screen

`axe describe-ui` dumps the full tree as JSON (verbose: frames, roles, pids…). For
deciding what to tap, flatten it to labels:

```bash
axe describe-ui --udid "$U" | python3 -c 'import json,sys
def w(n):
  for x in n:
    if x.get("AXLabel") or x.get("AXValue"):
      print(x["type"], "|", (x.get("AXLabel") or "").replace("\n"," / "), "|", x.get("AXValue") or "")
    w(x.get("children") or [])
w(json.load(sys.stdin))'
```

`axe describe-ui --udid "$U" --point 200,400` describes just the element at a point.

Prefer the tree over screenshots for navigation; take a screenshot when you need to
judge layout/visuals or show the user.

## Interaction

```bash
# Tap — by accessibility label / id / value, or raw coordinates (points).
# Label matching is exact — a partial label fails with "No accessibility element matched".
axe tap --label "Sign in"                 --udid "$U"
axe tap --label "Sign in" --element-type Button --udid "$U"   # disambiguate
axe tap --id "signin_button"              --udid "$U"         # accessibilityIdentifier
axe tap -x 200 -y 600                     --udid "$U"
axe tap --label "Dashboard" --wait-timeout 10 --udid "$U"     # poll until it appears

# Type into the focused field (tap the field first). US-keyboard chars only.
axe tap --label "Email" --udid "$U" && axe type 'james@local.dev' --udid "$U"
echo 'long text' | axe type --stdin --udid "$U"

# Scroll / swipe
axe gesture scroll-down --udid "$U"       # scroll-up|down|left|right, swipe-from-*-edge
axe swipe --start-x 200 --start-y 700 --end-x 200 --end-y 200 --udid "$U"

# Hardware buttons: home | lock | side-button | siri | apple-pay
axe button home --udid "$U"
```

**Batch** — one HID session, faster for multi-step flows (multi-word labels need inner
quotes):

```bash
axe batch --udid "$U" --wait-timeout 5 \
  --step "tap --label Email"    --step "type 'james@local.dev'" \
  --step "tap --label Password" --step "type 'LocalDev123!'" \
  --step "tap --label 'Sign in'" --step "sleep 2"
```

## Multiple simulators (multi-profile flows)

AXe and simctl both target by UDID, so drive two+ sims side by side (e.g. one user
requests, another claims). Boot an extra device and install the already-built app —
a Flutter debug `Runner.app` runs fine standalone on a sim:

```bash
B=<udid from: xcrun simctl list devices available>
xcrun simctl boot "$B" && xcrun simctl bootstatus "$B" -b
APP=clients/mobile/build/ios/iphonesimulator/Runner.app
BID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$APP/Info.plist")
xcrun simctl install "$B" "$APP" && xcrun simctl launch "$B" "$BID"
```

Without `flutter run` attached, read app logs with
`xcrun simctl spawn "$U" log stream --style compact --predicate 'process == "Runner"'`
(background it to a file; Flutter `print`s show up as `(Flutter) flutter: …`).
Relaunching the app via simctl detaches any running `flutter run`.

## Speaking to the app (voice input)

The simulator's mic can be fed synthetic speech through **BlackHole**, fully from the
CLI, with the bundled **`sim-say.sh`** (next to this file):

```bash
~/.claude/skills/ios-sim/sim-say.sh \
  --start "axe tap -x 201 -y 539 --udid $U >/dev/null" \
  "Could someone from my circle help me pick up groceries Saturday?"
```

It switches the **Mac's** default input to BlackHole (`SwitchAudioSource`), runs
`--start` (the tap that begins recording — the app opens its recorder on whatever
input is current at that moment, so the switch must come first), plays the text into
BlackHole with `say`, and **always restores the previous input** via an EXIT trap.
Then tap again to send. Options: `-v <say voice>`, `--pre <secs>` (wait before
speaking, default 1.5).

Setup (one-time): `brew install blackhole-2ch switchaudio-osx`, then
`sudo killall coreaudiod` (or reboot) for BlackHole to appear. The Simulator's
**I/O → Audio Input** must be **System** (default) so it follows the Mac's input — no
per-run menu clicks, and no sim reboot needed when the input switches.

Gotchas:
- If coreaudiod restarts while a sim is running, that sim's recorder breaks
  (`RecorderFailedToStartDeviceException` / `RecorderInitializeFailedException` in the
  app log) until you **reboot the sim** (`simctl shutdown` + `boot`).
- The Mac's real mic is unavailable for the few seconds a run takes.
- STT may emit a stray first partial (e.g. "Sim.") from the start chime — harmless.

Verified end to end on Penny (2026-10-08): real ElevenLabs STT transcribed `say` output
verbatim, with the Simulator on System input and no reboot.

## Screenshots & video

```bash
xcrun simctl io "$U" screenshot /path/shot.png        # pixel-perfect, no permissions
axe screenshot --udid "$U" --output /path/shot.png    # equivalent

# Cleaner marketing-style shots: freeze the status bar first
xcrun simctl status_bar "$U" override --time "9:41" --batteryState charged --batteryLevel 100
xcrun simctl status_bar "$U" clear
```

Write screenshots to the session scratchpad, not the repo.

**Video**: `axe record-video` (see `axe help record-video`), or simctl:
`xcrun simctl io "$U" recordVideo --codec h264 --force /path/run.mov` in the background,
drive the flow, then stop with **SIGINT** (`pkill -INT -f "simctl io .* recordVideo"`) —
any other signal leaves a corrupt file. Exit 130 is normal; wait for "Wrote video to:"
before reading it.

## Showing the user what you see

Screenshots you `Read` appear only in *your* tool output — the user can't see them.
Never say "see the screenshot above." To show them:

- **terminal-browser available** (`which terminal-browser`): write a small HTML page in
  the scratchpad that `<img>`s the PNGs (relative paths, side by side with captions) and
  open it with `terminal-browser new-tab <path.html>` (or
  `terminal-browser open <path.html> --split right` if no browser pane is open yet).
  One page per walkthrough works well.
- Otherwise: `open /path/shot.png` (Preview) or give them the path.

## App / device / context (simctl)

```bash
xcrun simctl listapps "$U" | grep -i <name>          # find installed bundle ids
xcrun simctl launch "$U" <bundle-id>
xcrun simctl terminate "$U" <bundle-id>
xcrun simctl openurl "$U" "pennyhelps://settings/profile"
xcrun simctl privacy "$U" grant <service> <bundle-id>   # see: xcrun simctl help privacy
xcrun simctl push "$U" <bundle-id> payload.apns
xcrun simctl location "$U" set 47.6062,-122.3321
axe list-simulators                                  # all sims with UDIDs/state
```

## Gotchas

- **Flutter tab labels include the position hint**: a bottom-nav item's AXLabel is
  literally `"Pins\nTab 3 of 3"`. Match the whole string (`--label $'Pins\nTab 3 of 3'`)
  or tap by coordinates from the tree's `frame`.
- **Flutter semantics**: widgets appear in the tree only if they expose semantics (most
  Material/Cupertino widgets do). If a control is missing, add `Semantics(label: …)` in
  the Flutter code, or fall back to `-x/-y` (points, from the tree's `frame`; screenshot
  pixels ÷ 3 on iPhone 17).
- **`axe type` is US-keyboard only** — no accented/international characters.
- **Fast typing drops characters** (seen: `george@local.dev` → `george@local`), especially
  in `batch` right after a tap. `sleep 1` after focusing a field, type in short chunks
  with ~0.4s pauses, and verify the field's `AXValue` before submitting. Clear a field
  with `axe key-combo --modifiers 227 --key 4` (Cmd+A) then `axe key 42` (delete).
- **Unlabeled controls** (e.g. Penny's big mic button) need `-x/-y`, and their position can
  shift between states — re-screenshot when a tap seems to do nothing, and check app logs
  to tell "tap missed" from "tap landed, feature failed".
- **System prompts** (notifications, permissions) appear in the tree like app UI —
  tap "Not now"/"Allow" by label, or pre-grant with `simctl privacy`.
- **Homebrew may nag "Xcode is outdated"** when installing/upgrading axe — advisory only.
  Don't upgrade Xcode as a side effect; it changes the simulator runtime the e2e
  attestation pins.

## Penny specifics

- Run the app: `make mobile-dev` (backgrounded) — `flutter run` against local Supabase
  and the API on `127.0.0.1:8080` (`make dev` or `make compose-up`). "Flutter run key
  commands." in the output means it's up; hot reload stays live.
- Seed users first: `make seed-dev-data notebooks=1` → `admin@` / `james@` /
  `george@local.dev`, password `LocalDev123!`, FTUX done, sample notebooks on James.
- First sign-in shows a "Turn on notifications?" sheet → tap "Not now".
- Home tabs: Ask / Circles / Pins; Memories (Notebooks / Chats / Saved) via
  Pins → "Go to Memories".
- **Sending to Penny is voice-only** ("View chat" is a read-only viewer), so creating a
  request needs the BlackHole recipe above. Mic button (unlabeled): ~(201, 539) on the
  resting Ask screen, ~(201, 620) once a session is open (iPhone 17). "Tap to send" in
  the tree = recording.
- Request → claim flow (verified with james@ on sim A, george@ on sim B): speak request →
  Penny's draft → "Send to my Circle" → B: Circles → "Circles I'm In" → "New requests" →
  "I'll help" → "Yes, I'll help" → A: Circles shows "George will help". Leaving Ask via
  "Done" asks "Done with this Ask session?" → "Yes, I'm done".
- Bundle ids: `ai.pennyhelps.pennyMobile` (prod flavor), `ai.pennyhelps.pennyMobile.dev`
  (dev flavor).
- For deterministic mobile e2e the repo uses Flutter `integration_test` (AGENTS.md → E2E
  Attestation). AXe is for *ad-hoc* driving, verification, and screenshots.

## Reference

- `axe help <subcommand>` for full flags (tap, type, swipe, gesture, batch, touch, drag,
  key, key-combo, slider, record-video, stream-video).
- `axe init` installs AXe's own upstream skill files for AI clients — not needed; this
  skill covers it.
