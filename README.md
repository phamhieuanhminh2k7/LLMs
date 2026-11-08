# Pixel Escape

A turn-based NumPy world with Pygame controls: reach the green exit alive.
Includes simulation and manual play only, without agents, training, or code generation.

## Install and play

Use Python 3.10 or newer. From the repository root:
```sh
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pixel_escape
```

- **Arrow keys / WASD:** move one tile per press.
- **Space:** wait for one step. **R:** start a new episode. **Escape:** quit.
- Blue is the player, gray is a wall, red is a hazard, and green is the exit.
- Walls and world boundaries block movement. Hazards are stationary and traversable.
- Each step ending on a hazard costs one health, including waiting or a blocked move.

You start with eight health. The HUD shows eight adjacent one-pixel segments:
bright yellow means remaining health and dark means depleted health. Its position
is randomized at reset and stays fixed throughout the episode. The HUD occupies
its own strip above the world, so it never covers tiles.

Zero health is failure; reaching the exit alive is success. Running out of steps
also ends play. The window title shows the outcome; press **R** to continue.
Idle display frames never advance the simulation. The resizable window uses
nearest-neighbor scaling; resizing does not change observation resolution.

## Configuration

Use command-line flags or pass the matching underscore names to `Config`:
| CLI flag | Default | Meaning |
| --- | ---: | --- |
| `--width` | 64 | Observation width in pixels |
| `--height` | 64 | Observation height, including HUD |
| `--tile-size` | 4 | Square world tile size in pixels |
| `--hud-height` | 4 | Height of reserved top strip |
| `--max-health` | 8 | Starting health and number of one-pixel HUD segments |
| `--wall-count` | 36 | Number of wall tiles |
| `--hazard-count` | 18 | Number of hazard tiles |
| `--max-steps` | 256 | Maximum actions per episode |
| `--scale` | 8 | Initial display enlargement; manual play only |
| `--seed` | unset | Seed for reproducible layouts; manual play only |

```sh
python -m pixel_escape --width 80 --height 68 --tile-size 4 --max-steps 400 --seed 7
```

Configuration values must be integers. Dimensions, tile size, HUD height, health,
and step limit must be positive; obstacle counts may be zero. Width and
`height - hud_height` must be divisible by tile size. The HUD must leave room for
the world, and `max_health <= width`. The world must have at least two cells;
wall and hazard counts together cannot exceed `columns * rows - 2`.
Invalid configurations raise `ValueError`.

Each reset randomizes the start, exit, walls, and hazards. Generation reserves a
hazard-free route that fits within the step limit, then places the exact requested
obstacle counts outside that route. Dense worlds may place the exit near the start.

## Use without a window

The environment imports only NumPy. This headless example waits until the time limit:

```python
from pixel_escape import Action, Config, EscapeEnv
env = EscapeEnv(Config(max_steps=10))
observation, info = env.reset(seed=7)
assert observation.shape == (64, 64, 3)
assert str(observation.dtype) == "uint8"
while True:
    observation, reward, terminated, truncated, info = env.step(Action.WAIT)
    if terminated or truncated:
        print(info["status"], reward)
        break
```

Actions are `UP=0`, `DOWN=1`, `LEFT=2`, `RIGHT=3`, and `WAIT=4`. Each call advances
exactly one step. Rewards are **+1** for success, **−1** for death, and **0** otherwise.
`terminated` marks success or death; `truncated` marks the time limit. Success or
death on the final allowed step takes precedence over truncation. Call `reset`
before the first step and after either ending; otherwise `step` raises `RuntimeError`.

Observations are fresh RGB `uint8` arrays with shape `(height, width, 3)` containing
pixels only. `env.render()` returns another observation without advancing time.
The separate `info` dictionary reports health, player/exit positions, walls,
hazards, step count, HUD position, and status. World coordinates are `(x, y)` in
tiles; HUD coordinates are pixels. `reset(seed=7)` restarts the random stream;
`reset()` continues it. Identical seeds and action/reset sequences reproduce
episodes with the pinned dependencies.

## Checks

```sh
python -m unittest discover -s tests -v
```

The simulation tests need no display. Pygame integration tests use SDL's dummy
video driver to check controls, scaling, resizing, and episode status without a window.
