"""Checks against real downloaded games. Missing games are failures, not passes."""

from contextlib import contextmanager
from unittest.mock import patch

import numpy as np

from .runtime import ENVIRONMENTS_DIR, load_game, make_arcade


@contextmanager
def no_network():
    """Fail on attempted HTTP or socket connections, even if the SDK catches them."""
    with (patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP attempted offline")) as http,
          patch("socket.socket.connect", side_effect=AssertionError("Socket attempted offline")) as connect,
          patch("socket.socket.connect_ex", side_effect=AssertionError("Socket attempted offline")) as connect_ex):
        yield
        http.assert_not_called()
        connect.assert_not_called()
        connect_ex.assert_not_called()


def verify_game(game_id="ls20", environments_dir=ENVIRONMENTS_DIR):
    from .viewer import to_rgb

    frame_counts, shapes, dtypes, values = [], set(), set(), set()

    def compare(observation, reference):
        assert observation is not None and reference is not None, "Official reset/action failed"
        assert observation.state == reference.state
        assert observation.available_actions == reference.available_actions
        assert observation.levels_completed == reference.levels_completed
        assert len(observation.frame) == len(reference.frame) > 0
        frame_counts.append(len(observation.frame))
        for frame, original in zip(observation.frame, reference.frame):
            assert frame.dtype == original.dtype
            np.testing.assert_array_equal(frame, original)
            before = frame.copy()
            rgb = to_rgb(frame)
            assert rgb.shape == (*frame.shape, 3)
            assert not np.shares_memory(rgb, frame)
            np.testing.assert_array_equal(frame, before)
            shapes.add(frame.shape)
            dtypes.add(str(frame.dtype))
            values.update(int(value) for value in np.unique(frame))

    with no_network():
        env = load_game(game_id, seed=0, environments_dir=environments_dir)
        # The reference is the official API directly, without integration helpers.
        reference = make_arcade(environments_dir).make(env.info.game_id, seed=0)
        compare(env.observation_space, reference.observation_space)
        compare(env.reset(), reference.reset())
        actions = list(env.action_space)
        assert actions, "No valid actions returned"
        for action in actions:
            compare(env.reset(), reference.reset())
            data = {"x": 0, "y": 0} if action.is_complex() else {}
            compare(env.step(action, data=data), reference.step(action, data=data))
    print(f"Verified {env.info.game_id}: reset + {len(actions)} available actions; no network calls.")
    print(f"Native shapes={sorted(shapes)}, dtypes={sorted(dtypes)}, color indices={sorted(values)}")
    print(f"Frames per response={frame_counts}; official frames unchanged after display conversion.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_id", nargs="?", default="ls20")
    verify_game(parser.parse_args().game_id)
