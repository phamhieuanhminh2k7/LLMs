"""Manual controls and display only; all rules stay in the official environment."""

from collections import deque
import time

import numpy as np
import pygame
from arc_agi.rendering import COLOR_MAP, hex_to_rgb
from arcengine import GameAction, GameState

PALETTE = np.array([hex_to_rgb(COLOR_MAP[i]) for i in range(len(COLOR_MAP))], dtype=np.uint8)
KEYS = {
    pygame.K_UP: GameAction.ACTION1, pygame.K_w: GameAction.ACTION1, pygame.K_1: GameAction.ACTION1,
    pygame.K_DOWN: GameAction.ACTION2, pygame.K_s: GameAction.ACTION2, pygame.K_2: GameAction.ACTION2,
    pygame.K_LEFT: GameAction.ACTION3, pygame.K_a: GameAction.ACTION3, pygame.K_3: GameAction.ACTION3,
    pygame.K_RIGHT: GameAction.ACTION4, pygame.K_d: GameAction.ACTION4, pygame.K_4: GameAction.ACTION4,
    pygame.K_SPACE: GameAction.ACTION5, pygame.K_f: GameAction.ACTION5, pygame.K_5: GameAction.ACTION5,
    pygame.K_z: GameAction.ACTION7, pygame.K_7: GameAction.ACTION7,
    pygame.K_r: GameAction.RESET,
}


def to_rgb(frame):
    """Allocate display RGB using the official palette; never modify index pixels."""
    if frame.ndim != 2 or not np.issubdtype(frame.dtype, np.integer):
        raise ValueError("Expected a native 2D integer color-index frame.")
    if frame.size == 0 or frame.min() < 0 or frame.max() >= len(PALETTE):
        raise ValueError("Frame contains values outside the official display palette.")
    return PALETTE[frame]


def native_click(position, rectangle, scale):
    """Map a displayed pixel to the same native pixel, with no logical tile grid."""
    if not rectangle.collidepoint(position):
        return None
    return {"x": (position[0] - rectangle.x) // scale,
            "y": (position[1] - rectangle.y) // scale}


class Viewer:
    def __init__(self, env, scale=8):
        if not isinstance(scale, int) or isinstance(scale, bool) or scale < 1:
            raise ValueError("scale must be a positive integer")
        self.env, self.scale = env, scale
        self.pending = deque()
        self.window = None
        self.frame_duration = 1 / max(1, env.info.default_fps or 5)
        self.accept(env.observation_space)

    def accept(self, observation):
        if observation is None or not observation.frame:
            raise RuntimeError("The official environment returned no frames.")
        self.observation = observation  # Keep every original array in its original order.
        self.frame_index = 0
        self.deadline = time.monotonic() + self.frame_duration

    def rectangle(self):
        height, width = self.observation.frame[self.frame_index].shape
        display_width = max(720, width * self.scale)
        return pygame.Rect((display_width - width * self.scale) // 2, 0,
                           width * self.scale, height * self.scale)

    def handle_event(self, event):
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            return False
        if event.type == pygame.KEYDOWN and event.key in KEYS:
            self.pending.append((KEYS[event.key], {}))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            data = native_click(event.pos, self.rectangle(), self.scale)
            if data is not None:
                self.pending.append((GameAction.ACTION6, data))
        return True

    def advance(self, now):
        # Play all frames of one response before submitting the next input.
        if now < self.deadline:
            return
        if self.frame_index + 1 < len(self.observation.frame):
            self.frame_index += 1
            self.deadline = now + self.frame_duration
        elif self.pending:
            action, data = self.pending.popleft()
            if action == GameAction.RESET:
                self.accept(self.env.reset())
            elif (self.observation.state not in (GameState.WIN, GameState.GAME_OVER)
                  and action in self.env.action_space):
                self.accept(self.env.step(action, data=data))

    def draw(self, font):
        frame = self.observation.frame[self.frame_index]
        rectangle = self.rectangle()
        size = (max(720, rectangle.width), rectangle.height + 110)
        if self.window is None or self.window.get_size() != size:
            self.window = pygame.display.set_mode(size)
        self.window.fill((20, 20, 20))
        surface = pygame.surfarray.make_surface(to_rgb(frame).transpose(1, 0, 2))
        self.window.blit(pygame.transform.scale(surface, rectangle.size), rectangle)
        available = ", ".join(action.name for action in self.env.action_space)
        lines = [
            "W/Up/1: ACTION1   S/Down/2: ACTION2   A/Left/3: ACTION3   D/Right/4: ACTION4",
            "Space/F/5: ACTION5   Left click: ACTION6 (native x,y)   Z/7: ACTION7",
            "R: official RESET   Esc: quit   Only currently available actions are sent.",
            f"Available: {available}",
            f"{self.observation.state.value} | levels: {self.observation.levels_completed}"
            f" | frame: {self.frame_index + 1}/{len(self.observation.frame)} | native: {frame.shape}",
        ]
        for index, line in enumerate(lines):
            self.window.blit(font.render(line, True, (235, 235, 235)), (8, rectangle.bottom + 3 + index * 21))
        pygame.display.set_caption(f"ARC-AGI-3 | {self.observation.game_id} | {self.observation.state.value}")
        pygame.display.flip()

    def run(self):
        pygame.display.init()
        pygame.font.init()
        pygame.key.set_repeat()
        font = pygame.font.Font(None, 20)
        clock = pygame.time.Clock()
        try:
            running = True
            while running:
                for event in pygame.event.get():
                    if not self.handle_event(event):
                        running = False
                        break
                if running:
                    self.advance(time.monotonic())
                    self.draw(font)
                    clock.tick(60)
        finally:
            pygame.quit()
