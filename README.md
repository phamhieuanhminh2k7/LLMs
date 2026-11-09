# Official ARC-AGI-3 local environments

This repository now contains an integration with the official
[ARC Prize Toolkit](https://github.com/arcprize/ARC-AGI) and
[ARCEngine](https://github.com/arcprize/ARCEngine) in `arc_local/`.
The earlier custom Pixel Escape game and its tests have been removed.
There are no learning agents, training code, or replacement game mechanics.

**Current status:** the integration and viewer checks pass, but **no official
game has been downloaded or successfully run in this cloud workspace yet**.
The cloud proxy blocks `three.arcprize.org` with HTTP 403, including the anonymous
key endpoint required for the official download. Run the download command below
on your own computer with Internet access, or allow that domain in the cloud
environment settings. `ls20` is the official quickstart game, not a locally
verified game in this checkout. The `verify` command fails if it is missing.

## Windows quickstart

Install **64-bit Python 3.12** ([Windows installer](https://www.python.org/downloads/release/python-31210/)).
In GitHub Desktop, fetch/pull `main`, then use **Repository → Show in Explorer**.
In that folder's address bar type `cmd` and press Enter. All commands below run
from the downloaded `LLMs` folder; `/workspace` is not a path on your computer.

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --only-binary=:all: -r arc_local\requirements.txt
.venv\Scripts\python -m arc_local download ls20
.venv\Scripts\python -m arc_local list
.venv\Scripts\python -m arc_local verify ls20
.venv\Scripts\python -m arc_local play ls20
```

Stop if installation or download fails; play requires a successful download.
If your old `.venv` uses a different Python version, recreate it with
`py -3.12 -m venv --clear .venv` first. This clears installed packages only.

## macOS / Linux

Open a terminal in this repository's folder, with Python 3.12 installed:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r arc_local/requirements.txt
.venv/bin/python -m arc_local download ls20
.venv/bin/python -m arc_local list
.venv/bin/python -m arc_local verify ls20
.venv/bin/python -m arc_local play ls20
```

After installation, use your environment's Python executable for every command.
The examples below abbreviate it to `python`.

## Downloads versus offline play

- `python -m arc_local catalogue`: fetch the public catalogue accessible to you (online).
- `python -m arc_local download ls20`: use the official Toolkit's `NORMAL` mode
  to download source and metadata, then reopen them in `OFFLINE` mode.
- `python -m arc_local list`: list complete local downloads only (offline).
- `python -m arc_local play GAME_ID --scale 8`: play a downloaded game (offline).
- `python -m arc_local.headless GAME_ID`: reset and take one valid action without a window (offline).

Downloads stay under `arc_local/environment_files/<game>/<version>/` as the
original Python source and `metadata.json`, plus a provenance/checksum file.
Game files are not rewritten. Existing version folders are never overwritten.
Use full versioned IDs from `list` to select a particular downloaded version.
You can disconnect from the Internet after a successful download and installation.

The official docs name `ls20`, `ft09`, and `vc33` as anonymous public examples.
**None is bundled in this checkout yet.** Use `catalogue` to discover current
availability before downloading another game. Additional public games require
a free account/API key from [ARC Prize](https://three.arcprize.org).
Set `ARC_API_KEY` in your local environment or an ignored `.env` file; never put
it in Python code or Git. An unset key uses the Toolkit's anonymous-key flow.
In Windows Command Prompt, use `set ARC_API_KEY=YOUR_KEY`; on macOS/Linux, use
`export ARC_API_KEY=YOUR_KEY`, replacing the placeholder with your own key.
Offline play needs no key. Private evaluation games are outside this integration.

Leave `OPERATION_MODE` and `ARC_BASE_URL` unset. The integration chooses its own
operation mode; it rejects competition mode before any connection is made.
The cloud setup needs `three.arcprize.org` for download and `docs.arcprize.org`
for web documentation; these network restrictions are separate from API keys.

## Manual controls

The local Toolkit provides visual renderers and a REST API but no local keyboard/
mouse player. This small Pygame viewer uses the official palette and mappings:

| Input | Official action |
| --- | --- |
| W / Up / 1 | ACTION1 |
| S / Down / 2 | ACTION2 |
| A / Left / 3 | ACTION3 |
| D / Right / 4 | ACTION4 |
| Space / F / 5 | ACTION5 (game-specific; not a generic wait) |
| Left click inside the image | ACTION6, with native pixel x/y coordinates |
| Z / 7 | ACTION7 |
| R | The original RESET action |
| Escape | Close the viewer |

Only actions currently exposed by the game are forwarded. Controls and status
appear below the image. Every frame returned by an action is displayed in order
at the game's metadata FPS before the next queued input is sent. No action runs
just because time passes. Enlargement affects the display only. Original rules,
sprites, movement increments, win/loss/reset behavior, and color-index arrays
are handled entirely by the official game and engine.

## Python API without a window

```python
from arc_local import load_game

env = load_game("ls20")                 # Explicit OFFLINE loading; no download.
observation = env.reset()               # Original FrameDataRaw, not a Gym tuple.
assert observation is not None
action = env.action_space[0]            # A currently supported official action.
data = {"x": 0, "y": 0} if action.is_complex() else {}
result = env.step(action, data=data)
assert result is not None

for frame in result.frame:              # Keep all frames, not only the last.
    print(frame.shape, frame.dtype)     # Native 2D color indices; no RGB conversion.
print(result.state, result.available_actions, result.levels_completed)
```

`load_game` returns the official `LocalEnvironmentWrapper` directly. Observations
are the official `FrameDataRaw` response and native NumPy arrays, with no extra
game-internal state, rewards, resizing, feature extraction, or agent interface.
The viewer allocates separate RGB arrays using `arc_agi.rendering.COLOR_MAP`.

## Verification and attribution

```sh
python -m unittest discover -s arc_local/tests -v
python -m arc_local verify ls20
```

The unit suite tests the integration boundary with synthetic pixel arrays, not
replacement games. Currently **11 checks pass and 1 real-game check is skipped**
because downloading is blocked. The manual display conversion and surface were
tested using SDL's dummy driver; actual official-game play is still unverified.
The official packages installed successfully on Python 3.12, and pip resolved
and downloaded prebuilt Windows x64 / Python 3.12 packages for all requirements.
That checks package availability, not Windows gameplay.

After download, `verify` checks real resets and available actions against the
official API directly, compares every native frame, and checks RGB conversion
doesn't change them. HTTP requests and socket connections are blocked during
these checks, so any attempted online gameplay fails verification.

See [sources and licenses](arc_local/THIRD_PARTY.md). Upstream game code is kept
separate from integration code; the integration does not define any ARC games.
