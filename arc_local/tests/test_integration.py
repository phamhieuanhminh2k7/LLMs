"""Integration boundary tests; synthetic pixels here are NOT ARC game fixtures."""

import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame
from arc_agi.rendering import frame_to_rgb_array
from arcengine import FrameDataRaw, GameAction, GameState

from arc_local.download import download_game
from arc_local.runtime import list_games, load_game, make_arcade
from arc_local.verify import no_network, verify_game
from arc_local.viewer import Viewer, native_click, to_rgb


def response(frames, actions=(1, 6, 7), state=GameState.NOT_FINISHED):
    observation = FrameDataRaw(game_id="viewer-unit-test", available_actions=list(actions), state=state)
    observation.frame = frames
    return observation


class RuntimeTests(unittest.TestCase):
    def test_empty_catalogue_and_missing_game_never_connect(self):
        with tempfile.TemporaryDirectory() as folder, no_network():
            self.assertEqual(list_games(folder), [])
            with self.assertRaisesRegex(FileNotFoundError, "download ls20"):
                load_game("ls20", environments_dir=folder)

    def test_offline_override_trap_is_rejected_before_connecting(self):
        with no_network(), patch.dict(os.environ, {"OPERATION_MODE": "competition"}):
            with self.assertRaisesRegex(RuntimeError, "Unset OPERATION_MODE"):
                make_arcade()

    def test_online_env_setting_cannot_change_offline_loading(self):
        with tempfile.TemporaryDirectory() as folder, no_network(), patch.dict(os.environ, {"OPERATION_MODE": "online"}):
            self.assertEqual(list_games(folder), [])

    def test_download_rejects_online_and_custom_service_settings(self):
        with no_network(), patch.dict(os.environ, {"OPERATION_MODE": "online"}):
            with self.assertRaisesRegex(RuntimeError, "OPERATION_MODE"):
                make_arcade(download=True)
        with no_network(), patch.dict(os.environ, {"OPERATION_MODE": "normal", "ARC_BASE_URL": "https://example.com"}):
            with self.assertRaisesRegex(RuntimeError, "ARC_BASE_URL"):
                make_arcade(download=True)

    def test_failed_download_does_not_leave_partial_game_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "environment_files"
            with patch("arc_local.download.make_arcade", side_effect=RuntimeError("download blocked")):
                with self.assertRaisesRegex(RuntimeError, "download blocked"):
                    download_game("ls20", target)
            self.assertEqual(list(Path(folder).iterdir()), [])


class DisplayTests(unittest.TestCase):
    def test_palette_matches_official_renderer_without_changing_native_arrays(self):
        native = np.arange(16, dtype=np.int8).reshape(2, 8)
        before = native.copy()
        rgb = to_rgb(native)
        np.testing.assert_array_equal(rgb, frame_to_rgb_array(0, native, scale=1))
        np.testing.assert_array_equal(native, before)
        self.assertEqual(native.dtype, np.int8)
        self.assertFalse(np.shares_memory(rgb, native))

    def test_click_coordinates_are_native_pixels_not_tiles(self):
        rect = pygame.Rect(12, 10, 80, 48)
        self.assertEqual(native_click((12, 10), rect, 4), {"x": 0, "y": 0})
        self.assertEqual(native_click((91, 57), rect, 4), {"x": 19, "y": 11})
        self.assertIsNone(native_click((92, 58), rect, 4))
        self.assertIsNone(native_click((11, 10), rect, 4))

    def test_all_frames_are_presented_before_a_pending_action(self):
        frames = [np.full((3, 5), color, dtype=np.int8) for color in (1, 9, 14)]
        observation = response(frames)
        env = SimpleNamespace(observation_space=observation, info=SimpleNamespace(default_fps=5),
                              action_space=[GameAction.ACTION1])
        from unittest.mock import Mock
        env.step = Mock(return_value=response([frames[-1]]))
        viewer = Viewer(env)
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        viewer.advance(viewer.deadline)
        self.assertEqual(viewer.frame_index, 1)
        env.step.assert_not_called()
        viewer.advance(viewer.deadline)
        self.assertEqual(viewer.frame_index, 2)
        env.step.assert_not_called()
        viewer.advance(viewer.deadline)
        env.step.assert_called_once_with(GameAction.ACTION1, data={})
        self.assertEqual(len(observation.frame), 3)
        for frame, color in zip(frames, (1, 9, 14)):
            np.testing.assert_array_equal(frame, np.full((3, 5), color, dtype=np.int8))

    def test_mouse_supported_actions_and_original_reset_are_forwarded(self):
        from unittest.mock import Mock
        observation = response([np.zeros((12, 20), dtype=np.int8)])
        env = SimpleNamespace(observation_space=observation, info=SimpleNamespace(default_fps=5),
                              action_space=[GameAction.ACTION6, GameAction.ACTION7],
                              step=Mock(return_value=observation), reset=Mock(return_value=observation))
        viewer = Viewer(env, scale=4)
        rect = viewer.rectangle()
        viewer.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                              pos=(rect.x + 19 * 4 + 3, 11 * 4 + 2)))
        viewer.advance(viewer.deadline)
        env.step.assert_called_with(GameAction.ACTION6, data={"x": 19, "y": 11})
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
        viewer.advance(viewer.deadline)
        env.step.assert_called_with(GameAction.ACTION7, data={})
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        viewer.advance(viewer.deadline)
        self.assertEqual(env.step.call_count, 2)  # ACTION5 is unavailable.
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        viewer.advance(viewer.deadline)
        env.reset.assert_called_once_with()

    def test_nearest_neighbor_surface_has_native_pixels_and_separate_controls(self):
        native = np.arange(16, dtype=np.int8).reshape(2, 8)
        env = SimpleNamespace(observation_space=response([native]), info=SimpleNamespace(default_fps=5),
                              action_space=[GameAction.ACTION1])
        viewer = Viewer(env, scale=4)
        pygame.display.init()
        pygame.font.init()
        try:
            viewer.draw(pygame.font.Font(None, 20))
            rect = viewer.rectangle()
            pixels = pygame.surfarray.array3d(viewer.window).transpose(1, 0, 2)
            game_pixels = pixels[rect.y:rect.bottom, rect.x:rect.right]
            np.testing.assert_array_equal(game_pixels, np.repeat(np.repeat(to_rgb(native), 4, axis=0), 4, axis=1))
            self.assertEqual(viewer.window.get_height(), rect.height + 110)
            np.testing.assert_array_equal(native, np.arange(16, dtype=np.int8).reshape(2, 8))
        finally:
            pygame.quit()

    def test_idle_and_game_over_do_not_advance_the_environment(self):
        from unittest.mock import Mock
        observation = response([np.zeros((4, 6), dtype=np.int8)], state=GameState.GAME_OVER)
        env = SimpleNamespace(observation_space=observation, info=SimpleNamespace(default_fps=5),
                              action_space=[GameAction.ACTION1], step=Mock())
        viewer = Viewer(env)
        viewer.advance(viewer.deadline)
        viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        viewer.advance(viewer.deadline)
        env.step.assert_not_called()


class DownloadedGameTests(unittest.TestCase):
    def test_actual_official_games_with_network_disabled(self):
        games = list_games()
        if not games:
            self.skipTest("No official game downloaded: real reset/action verification is BLOCKED.")
        for game in games:
            with self.subTest(game_id=game.game_id):
                verify_game(game.game_id)


if __name__ == "__main__":
    unittest.main()
