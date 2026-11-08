"""Rule and observation checks; no display or Pygame initialization required."""

from collections import deque
import unittest

import numpy as np

from pixel_escape import Action, Config, EscapeEnv


class EnvironmentTests(unittest.TestCase):
    def world(self, **overrides):
        options = dict(width=20, height=20, tile_size=4, hud_height=4,
                       max_health=8, wall_count=0, hazard_count=0, max_steps=20)
        options.update(overrides)
        env = EscapeEnv(Config(**options))
        env.reset(seed=1)
        env.player = (1, 1)
        env.exit = (4, 3)
        env.walls = set()
        env.hazards = set()
        return env

    def test_each_direction_and_wait_advance_exactly_one_step(self):
        env = self.world()
        for index, (action, expected) in enumerate([
            (Action.UP, (1, 0)), (Action.DOWN, (1, 1)),
            (Action.LEFT, (0, 1)), (Action.RIGHT, (1, 1)),
            (Action.WAIT, (1, 1)),
        ], start=1):
            _, reward, terminated, truncated, info = env.step(action)
            self.assertEqual(info["player"], expected)
            self.assertEqual(info["steps"], index)
            self.assertEqual(reward, 0)
            self.assertFalse(terminated or truncated)

    def test_walls_block_movement(self):
        env = self.world()
        env.walls = {(2, 1)}
        _, _, _, _, info = env.step(Action.RIGHT)
        self.assertEqual(info["player"], (1, 1))
        self.assertEqual(info["steps"], 1)

    def test_all_four_boundaries_block_movement(self):
        for position, action in [
            ((0, 1), Action.LEFT), ((4, 1), Action.RIGHT),
            ((1, 0), Action.UP), ((1, 3), Action.DOWN),
        ]:
            with self.subTest(position=position):
                env = self.world()
                env.player = position
                _, _, _, _, info = env.step(action)
                self.assertEqual(info["player"], position)
                self.assertEqual(info["steps"], 1)

    def test_enter_wait_and_blocked_movement_on_hazard_each_damage(self):
        env = self.world()
        env.hazards = {(2, 1)}
        env.walls = {(3, 1)}
        for action, health in [(Action.RIGHT, 7), (Action.WAIT, 6),
                               (Action.RIGHT, 5)]:
            _, reward, terminated, truncated, info = env.step(action)
            self.assertEqual(info["player"], (2, 1))
            self.assertEqual(info["health"], health)
            self.assertEqual(reward, 0)
            self.assertFalse(terminated or truncated)
        env.step(Action.LEFT)
        self.assertEqual(env.health, 5)
        self.assertEqual(env.hazards, {(2, 1)})

    def test_blocked_boundary_on_hazard_damages(self):
        env = self.world()
        env.player = (0, 1)
        env.hazards = {(0, 1)}
        env.step(Action.LEFT)
        self.assertEqual(env.health, 7)

    def test_death_after_eight_damage_steps(self):
        env = self.world()
        env.hazards = {env.player}
        for _ in range(7):
            _, reward, terminated, truncated, _ = env.step(Action.WAIT)
            self.assertEqual(reward, 0)
            self.assertFalse(terminated or truncated)
        _, reward, terminated, truncated, info = env.step(Action.WAIT)
        self.assertEqual(info["health"], 0)
        self.assertEqual(info["status"], "death")
        self.assertEqual(reward, -1)
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        with self.assertRaises(RuntimeError):
            env.step(Action.WAIT)

    def test_exit_gives_success_reward(self):
        env = self.world()
        env.exit = (2, 1)
        _, reward, terminated, truncated, info = env.step(Action.RIGHT)
        self.assertEqual(reward, 1)
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertEqual(info["status"], "success")
        self.assertEqual(info["health"], 8)
        with self.assertRaises(RuntimeError):
            env.step(Action.WAIT)

    def test_time_limit_is_distinct_from_termination(self):
        env = self.world(max_steps=2)
        self.assertFalse(env.step(Action.WAIT)[3])
        _, reward, terminated, truncated, info = env.step(Action.WAIT)
        self.assertEqual(reward, 0)
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertEqual(info["status"], "time_limit")
        self.assertEqual(info["steps"], 2)
        with self.assertRaises(RuntimeError):
            env.step(Action.WAIT)

    def test_success_and_death_take_priority_on_final_step(self):
        for ending in ("success", "death"):
            with self.subTest(ending=ending):
                env = self.world(max_steps=1)
                if ending == "success":
                    env.exit = (2, 1)
                else:
                    env.health = 1
                    env.hazards = {(2, 1)}
                _, reward, terminated, truncated, info = env.step(Action.RIGHT)
                self.assertEqual(reward, 1 if ending == "success" else -1)
                self.assertTrue(terminated)
                self.assertFalse(truncated)
                self.assertEqual(info["status"], ending)

    def test_reset_restores_episode_after_death(self):
        env = self.world()
        env.health = 1
        env.hazards = {env.player}
        env.step(Action.WAIT)
        _, info = env.reset(seed=2)
        self.assertEqual(info["health"], 8)
        self.assertEqual(info["steps"], 0)
        self.assertEqual(info["status"], "playing")
        self.assertFalse(env.terminated or env.truncated)
        env.step(Action.WAIT)

    def test_step_requires_reset(self):
        with self.assertRaises(RuntimeError):
            EscapeEnv().step(Action.WAIT)

    def test_invalid_actions_do_not_advance_world(self):
        env = self.world()
        for action in (-1, 5, "up", 1.0, True, None):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    env.step(action)
                self.assertEqual(env.steps, 0)
                self.assertEqual(env.player, (1, 1))
        env.step(int(Action.RIGHT))
        self.assertEqual(env.player, (2, 1))

    def test_observation_is_fresh_rgb_uint8_array(self):
        env = EscapeEnv()
        observation, info = env.reset(seed=11)
        self.assertIsInstance(observation, np.ndarray)
        self.assertEqual(observation.shape, (64, 64, 3))
        self.assertEqual(observation.dtype, np.uint8)
        self.assertEqual(info["health"], 8)
        expected = observation.copy()
        observation[:] = 0
        np.testing.assert_array_equal(env.render(), expected)
        info["health"] = -100
        info["player"] = (-100, -100)
        self.assertEqual(env.health, 8)
        self.assertNotEqual(env.player, (-100, -100))
        next_observation = env.step(Action.WAIT)[0]
        self.assertEqual(next_observation.shape, (64, 64, 3))
        self.assertEqual(next_observation.dtype, np.uint8)
        self.assertFalse(np.shares_memory(observation, next_observation))

    def test_nondefault_resolution_and_health(self):
        config = Config(width=80, height=52, tile_size=8, hud_height=4,
                        max_health=5, wall_count=7, hazard_count=4, max_steps=30)
        env = EscapeEnv(config)
        observation, info = env.reset(seed=7)
        self.assertEqual(observation.shape, (52, 80, 3))
        self.assertEqual(info["health"], 5)
        self.assertEqual(len(env.walls), 7)
        self.assertEqual(len(env.hazards), 4)
        self.assertEqual(env.step(Action.WAIT)[0].shape, (52, 80, 3))

    def test_seed_reproduces_layout_pixels_and_action_sequence(self):
        first, second = EscapeEnv(), EscapeEnv()
        first_obs, first_info = first.reset(seed=1234)
        second_obs, second_info = second.reset(seed=1234)
        np.testing.assert_array_equal(first_obs, second_obs)
        self.assertEqual(first_info, second_info)
        for action in (Action.UP, Action.LEFT, Action.WAIT, Action.DOWN,
                       Action.RIGHT) * 2:
            left, right = first.step(action), second.step(action)
            np.testing.assert_array_equal(left[0], right[0])
            self.assertEqual(left[1:], right[1:])
            if left[2] or left[3]:
                break
        # Omitting a seed continues each environment's own seeded RNG stream.
        for _ in range(3):
            first_obs, first_info = first.reset()
            second_obs, second_info = second.reset()
            np.testing.assert_array_equal(first_obs, second_obs)
            self.assertEqual(first_info, second_info)
        repeated_obs, repeated_info = first.reset(seed=1234)
        original_obs, original_info = EscapeEnv().reset(seed=1234)
        np.testing.assert_array_equal(repeated_obs, original_obs)
        self.assertEqual(repeated_info, original_info)

    def test_health_bar_has_one_pixel_segments_and_stays_fixed(self):
        env = self.world()
        x, y = env.health_bar
        self.assertGreaterEqual(x, 0)
        self.assertLessEqual(x + 8, 20)
        self.assertGreaterEqual(y, 0)
        self.assertLess(y, 4)
        before = env.render()
        bright = before[y, x].copy()
        np.testing.assert_array_equal(before[y, x:x + 8],
                                      np.tile(bright, (8, 1)))
        env.hazards = {env.player}
        before = env.render()
        after, _, _, _, info = env.step(Action.WAIT)
        self.assertEqual(info["health_bar"], (x, y))
        np.testing.assert_array_equal(after[y, x:x + 7],
                                      np.tile(bright, (7, 1)))
        self.assertLess(int(after[y, x + 7].sum()), int(bright.sum()))
        changed_pixels = np.any(before != after, axis=2)
        self.assertEqual(int(changed_pixels.sum()), 1)
        self.assertTrue(changed_pixels[y, x + 7])
        for _ in range(6):
            env.step(Action.WAIT)
            self.assertEqual(env.health_bar, (x, y))

    def test_reset_randomizes_bar_and_layout(self):
        env = EscapeEnv()
        bars, layouts = set(), set()
        for seed in range(20):
            _, info = env.reset(seed=seed)
            bars.add(info["health_bar"])
            layouts.add((env.player, env.exit, frozenset(env.walls),
                         frozenset(env.hazards)))
        self.assertGreater(len(bars), 1)
        self.assertGreater(len(layouts), 1)

    def test_generated_layouts_have_exact_counts_and_safe_routes(self):
        configs = [Config(), Config(width=12, height=12, tile_size=4,
                                    hud_height=4, max_health=8,
                                    wall_count=2, hazard_count=2, max_steps=5)]
        for config in configs:
            env = EscapeEnv(config)
            columns = config.width // config.tile_size
            rows = (config.height - config.hud_height) // config.tile_size
            for seed in range(40):
                with self.subTest(config=config, seed=seed):
                    env.reset(seed=seed)
                    self.assertNotEqual(env.player, env.exit)
                    self.assertEqual(len(env.walls), config.wall_count)
                    self.assertEqual(len(env.hazards), config.hazard_count)
                    self.assertFalse(env.walls & env.hazards)
                    blocked = env.walls | env.hazards
                    self.assertNotIn(env.player, blocked)
                    self.assertNotIn(env.exit, blocked)
                    for x, y in blocked | {env.player, env.exit}:
                        self.assertTrue(0 <= x < columns and 0 <= y < rows)
                    queue, visited = deque([env.player]), {env.player}
                    while queue:
                        x, y = queue.popleft()
                        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                            neighbor = (x + dx, y + dy)
                            if (0 <= neighbor[0] < columns
                                    and 0 <= neighbor[1] < rows
                                    and neighbor not in blocked
                                    and neighbor not in visited):
                                visited.add(neighbor)
                                queue.append(neighbor)
                    self.assertIn(env.exit, visited)

    def test_rejects_incompatible_configurations(self):
        for change in [
            {"width": 0}, {"height": 0}, {"tile_size": 0},
            {"hud_height": 0}, {"hud_height": 64}, {"width": 63},
            {"height": 63}, {"max_health": 0}, {"max_health": 65},
            {"wall_count": -1}, {"hazard_count": -1},
            {"wall_count": 239, "hazard_count": 0},
            {"max_steps": 0}, {"tile_size": 4.0}, {"max_steps": True},
        ]:
            with self.subTest(change=change):
                with self.assertRaises((ValueError, TypeError)):
                    Config(**change)


if __name__ == "__main__":
    unittest.main()
