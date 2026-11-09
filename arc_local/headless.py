"""Minimal example: python -m arc_local.headless ls20 (no window or network)."""

import argparse

from .runtime import load_game


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_id", nargs="?", default="ls20")
    args = parser.parse_args()
    env = load_game(args.game_id)
    observation = env.reset()
    if observation is None:
        raise RuntimeError("Official reset failed")
    print("Reset:", observation.state.value, [frame.shape for frame in observation.frame])

    action = env.action_space[0]  # A currently available official action.
    # ACTION6 uses native display pixel coordinates, not logical cells.
    data = {"x": 0, "y": 0} if action.is_complex() else {}
    result = env.step(action, data=data)
    if result is None:
        raise RuntimeError("Official step failed")
    print(action.name, "->", result.state.value, "levels:", result.levels_completed)
    for index, frame in enumerate(result.frame):  # Preserve ALL returned frames.
        print(index, frame.shape, frame.dtype, "color indices:", int(frame.min()), int(frame.max()))


if __name__ == "__main__":
    main()
