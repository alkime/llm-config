---
name: ios-sim
description: Drive the iOS Simulator from the CLI — launch apps, tap/type/swipe, read the UI accessibility tree, capture screenshots, set permissions/location/deep-links. Use when the user wants to interact with an iOS app on the Simulator, take simulator screenshots, automate or test a Flutter/iOS app's UI, or reproduce a flow on the booted simulator. The iOS analog of playwright-cli.
---

# iOS Simulator automation with SimPilot + simctl

Two tools, used together:

- **`xcrun simctl`** — Apple-native, always installed. Boot, install/launch apps,
  **screenshots**, video, deep links, permissions, status bar. No tap/type.
- **`simpilot`** ([SimPilot](https://github.com/ygrec-app/SimPilot), "Playwright for
  iOS") — the interaction layer: **tap, type, swipe, read the accessibility tree,
  assert, wait**. No idb required. Built from source at `~/dev/tools/SimPilot`,
  symlinked to `~/.local/bin/simpilot`.

Use **simpilot for interaction** and **simctl for screenshots** (see Gotchas — SimPilot's
own `screenshot` aborts on this macOS without Screen Recording permission, and the
simctl framebuffer capture is pixel-perfect and permission-free anyway).

## Critical: always target the booted device

SimPilot's `--device` flag takes a device **name** (not a UDID) and defaults to a
hardcoded `iPhone 16 Pro` that usually doesn't exist → `Simulator not found`. Resolve
the booted device name once and pass it to every command:

```bash
DEV=$(xcrun simctl list devices booted | sed -n 's/^[[:space:]]*\(.*\) ([0-9A-F-]\{36\}) (Booted).*/\1/p' | head -1)
echo "$DEV"   # e.g. "iPhone 17 Pro"
```

Then `simpilot <cmd> ... --device "$DEV"` throughout. `xcrun simctl ... booted` needs
no name — it auto-picks the booted device.

## Quick start

```bash
DEV=$(xcrun simctl list devices booted | sed -n 's/^[[:space:]]*\(.*\) ([0-9A-F-]\{36\}) (Booted).*/\1/p' | head -1)

simpilot tree --device "$DEV" --max-depth 6     # see what's on screen (scope the noise)
simpilot tap   --label "Email" --device "$DEV"  # tap by accessibility label
simpilot type  --text "james@local.dev" --device "$DEV"
xcrun simctl io booted screenshot /tmp/step.png # capture (NOT simpilot screenshot)
open /tmp/step.png
```

Keep the **Simulator window visible and frontmost** while tapping/typing — SimPilot
injects HID events at on-screen coordinates. Bring it forward with:
`open -a Simulator`.

## Interaction (simpilot)

```bash
# Find / read the UI — prefer this over screenshots for deciding what to tap.
simpilot tree   --device "$DEV"                 # full accessibility tree
simpilot tree   --device "$DEV" --max-depth 6   # trim depth (tree is verbose)
simpilot tree   --device "$DEV" --format json   # machine-readable

# Tap — targeting precedence: prefer --id, then --label, then --text (OCR fallback).
simpilot tap --id   "signin_button"  --device "$DEV"   # accessibility identifier
simpilot tap --label "Sign in"       --device "$DEV"   # accessibility label
simpilot tap --text  "Sign in"       --device "$DEV"   # visible text via OCR
simpilot tap --label "Sign in" --type button --device "$DEV"  # disambiguate by element type
# Optional: --timeout <secs> (default 5)

# Type — optionally focus a field first by id/label, else types into current focus.
simpilot type --text "hello"                         --device "$DEV"
simpilot type --text "secret" --label "Password"     --device "$DEV"
simpilot type --text "x"      --field "password_fld" --device "$DEV"   # focus by a11y id

# Swipe — direction is a positional arg.
simpilot swipe up    --device "$DEV"
simpilot swipe down  --distance 500 --device "$DEV"   # up | down | left | right

# Assert / wait — useful as flow gates and in scripts (non-zero exit on failure).
simpilot wait   --text "Dashboard"  --timeout 10 --device "$DEV"
simpilot assert visible     --label "Sign in"   --device "$DEV"
simpilot assert not-visible --text  "Spinner"   --device "$DEV"
```

There is **no coordinate (x/y) tap** in this build — only id/label/text. If a control
can't be found by any of those, it likely lacks an accessibility label (see Flutter note).

## App / device / context (simpilot OR simctl)

```bash
# Apps
simpilot app launch    <bundle-id>        --device "$DEV"
simpilot app install   <path/to.app>      --device "$DEV"
simpilot app terminate <bundle-id>        --device "$DEV"
xcrun simctl launch booted <bundle-id>                     # native equivalent
xcrun simctl listapps booted | grep -i <name>              # find an installed bundle id

# Deep links / universal links
simpilot url "pennyhelps://settings/profile" --device "$DEV"
xcrun simctl openurl booted "https://app.staging.pennyhelps.ai/..."

# Permissions, push, location
simpilot permission grant-all <bundle-id>      --device "$DEV"
simpilot permission set <...>                  --device "$DEV"   # see: simpilot permission set --help
simpilot push "Title" "Body" --bundle-id <id>  --device "$DEV"
simpilot location 48.8566 2.3522               --device "$DEV"

# Devices
simpilot devices list
simpilot devices boot     "iPhone 17 Pro"
simpilot devices shutdown "iPhone 17 Pro"
```

## Screenshots (use simctl — most reliable)

```bash
xcrun simctl io booted screenshot /tmp/shot.png            # pixel-perfect, no permissions
xcrun simctl io booted screenshot --type jpeg /tmp/shot.jpg

# Cleaner marketing-style shots: freeze the status bar first
xcrun simctl status_bar booted override \
  --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3
xcrun simctl status_bar booted clear                       # undo
```

`simpilot screenshot` exists but aborts here (`CGS_REQUIRE_INIT`) unless the terminal
has **Screen Recording** permission — don't rely on it; use the simctl line above.

## Video recording (simctl — record a whole flow)

`xcrun simctl io booted recordVideo` records the device display to a `.mov`. SimPilot
has no video command — this is pure simctl. **The file is only finalized on SIGINT** —
the recorder runs until interrupted, then writes the movie. Killing it any other way
(SIGKILL/SIGTERM) leaves a corrupt/empty file.

Agent-safe pattern — **start in the background, drive actions, stop with SIGINT**:

```bash
DEV=$(xcrun simctl list devices booted | sed -n 's/^[[:space:]]*\(.*\) ([0-9A-F-]\{36\}) (Booted).*/\1/p' | head -1)

# 1. Start recording in the background (run_in_background, or `&` in a plain shell).
#    --force overwrites an existing file; --codec h264 is widely compatible (default is hevc).
xcrun simctl io booted recordVideo --codec h264 --force /tmp/run.mov   # background this

# 2. simctl prints "Recording started" to stderr once the first frame lands — wait for it.

# 3. Drive the flow.
simpilot tap  --label "Email"    --device "$DEV"
simpilot type --text "james@local.dev" --device "$DEV"
simpilot tap  --label "Sign in"  --device "$DEV"

# 4. Stop with SIGINT — NOT SIGKILL. The recorder finalizes and exits.
pkill -INT -f "simctl io booted recordVideo"
#   or, if you captured the PID:  kill -INT "$REC_PID"
```

Notes:
- A **non-zero exit (130)** from the recorder is normal — it was terminated by a signal;
  the `.mov` is still written. Confirm with `xcrun ffprobe -show_format /tmp/run.mov`.
- Finalizing takes a beat after SIGINT ("Recording completed. Writing to disk." →
  "Wrote video to: …"). Don't read the file until that line appears.
- Options: `--codec h264|hevc`, `--display internal|external`, `--mask ignored|black`,
  `--force`. Default codec is `hevc` (smaller, but h264 plays more places).
- Only ~one recorder at a time per device; the broad `pkill -f` above stops any of them.

## Scripted flows (YAML)

For repeatable multi-step runs (e.g. capturing a whole login → dashboard journey),
SimPilot runs a YAML flow with built-in waits/asserts/screenshots:

```bash
simpilot run flow.yaml --device "$DEV" --output ./shots
simpilot run flow.yaml --device "$DEV" --dry-run    # print parsed steps, run nothing
```

Reach for this when the same sequence will be replayed; otherwise the one-off commands
above are simpler. (`--device` here overrides the device named inside the flow file.)

## Gotchas

- **Always pass `--device "$DEV"`** — the default `iPhone 16 Pro` won't exist (see top).
- **Window must be visible & frontmost** for tap/type/swipe (HID injection). `open -a Simulator`.
- **Screenshots via simctl, not simpilot** (window-server abort without Screen Recording perm).
- **`simpilot tree` is noisy** — it reads the *host* macOS accessibility tree, so it
  includes Simulator.app's menu bar (Apple/File/Edit/…). The device UI is under the
  `iPhone … – iOS …` node. Use `--max-depth`, `--format json`, or grep to cut the noise.
- **Flutter apps**: widgets surface in the tree **only if they expose semantics**
  (most Material/Cupertino widgets do — we confirmed Email/Password/"Sign in" on Penny).
  If a control isn't found by id/label, wrap it in a `Semantics(label: ...)` in the
  Flutter code, or fall back to `--text` (OCR). No x/y tap exists as a last resort.
- **Permissions needed once**: Accessibility (for tree/tap — already granted) and,
  only if you want `simpilot screenshot`, Screen Recording. TCC grants apply after a
  full terminal restart.

## Penny specifics

- Booted dev sim: **iPhone 17 Pro** (iOS 26.3). The `$DEV` snippet resolves it generically.
- Bundle ids: `ai.pennyhelps.pennyMobile` (prod flavor) and `ai.pennyhelps.pennyMobile.dev`
  (dev flavor). Confirm what's installed: `xcrun simctl listapps booted | grep -i penny`.
- Mobile app source: `clients/mobile`. Build/run it the normal way (`make mobile-*` /
  `flutter run` from there) if no Penny bundle is installed on the sim yet.
- For deterministic mobile e2e the repo already uses Flutter `integration_test` (see
  AGENTS.md → E2E Attestation). SimPilot is for *ad-hoc* driving/screenshots, not a
  replacement for that attested suite.

## Reference

- SimPilot repo: https://github.com/ygrec-app/SimPilot (Swift, MIT, early-stage —
  built from source; no Homebrew formula yet)
- Full flag help: `simpilot <subcommand> --help`
