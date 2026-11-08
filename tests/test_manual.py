"""Exercise the real Pygame loop and surfaces without requiring a desktop."""

import os
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame

from pixel_escape import Config, EscapeEnv
from pixel_escape.manual import run


class ManualTests(unittest.TestCase):
    def test_idle_wait_timeout_reset_resize_and_quit(self):
        env = EscapeEnv(Config(width=80, height=68, max_steps=2))
        events = [None, pygame.K_SPACE, None, pygame.K_SPACE,
                  pygame.K_SPACE, pygame.K_r, pygame.K_ESCAPE]
        expected_steps = [0, 0, 1, 1, 2, 2, 0]
        frame = 0

        def next_events():
            nonlocal frame
            self.assertEqual(env.steps, expected_steps[frame])
            self.assertEqual(env.render().shape, (68, 80, 3))
            if frame == 1:
                # Exact pixels, correct HWC orientation, nearest-neighbor scaling.
                displayed = pygame.surfarray.array3d(pygame.display.get_surface())
                np.testing.assert_array_equal(displayed.transpose(1, 0, 2)[::3, ::3], env.render())
                pygame.display.set_mode((500, 300), pygame.RESIZABLE)
            if frame in (4, 5):
                self.assertIn("FAILURE: time limit", pygame.display.get_caption()[0])
            if frame == 6:
                self.assertFalse(env.terminated or env.truncated)
                self.assertEqual(env.health, 8)
            key = events[frame]
            frame += 1
            return [] if key is None else [pygame.event.Event(pygame.KEYDOWN, key=key)]

        with patch("pygame.event.get", side_effect=next_events):
            run(env, seed=10, scale=3)
        self.assertEqual(frame, len(events))
        self.assertFalse(pygame.display.get_init())

    def test_movement_keys_and_success_title(self):
        env = EscapeEnv(Config(wall_count=0, hazard_count=0))
        keys = [pygame.K_UP, pygame.K_s, pygame.K_LEFT, pygame.K_d,
                pygame.K_w, pygame.K_DOWN, pygame.K_a, pygame.K_RIGHT,
                pygame.K_RIGHT, pygame.K_RIGHT]
        positions = [(2, 2), (2, 1), (2, 2), (1, 2), (2, 2),
                     (2, 1), (2, 2), (1, 2), (2, 2), (3, 2), (4, 2)]
        frame = 0

        def next_events():
            nonlocal frame
            if frame == 0:
                env.player, env.exit = positions[0], positions[-1]
            self.assertEqual(env.player, positions[frame])
            self.assertEqual(env.steps, frame)
            if frame == len(keys):
                self.assertTrue(env.terminated)
                self.assertIn("SUCCESS", pygame.display.get_caption()[0])
                return [pygame.event.Event(pygame.QUIT)]
            key = keys[frame]
            frame += 1
            return [pygame.event.Event(pygame.KEYDOWN, key=key)]

        with patch("pygame.event.get", side_effect=next_events):
            run(env, seed=1)
        self.assertEqual(frame, len(keys))


if __name__ == "__main__":
    unittest.main()
