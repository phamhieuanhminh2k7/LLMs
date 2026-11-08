"""Deterministic, turn-based rules and NumPy rendering. Coordinates are (x, y)."""

from dataclasses import dataclass, fields
from enum import IntEnum
from numbers import Integral

import numpy as np


class Action(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    WAIT = 4


DELTAS = ((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0))
BACKGROUND = (18, 24, 32)
WALL = (130, 140, 155)
HAZARD = (240, 65, 55)
EXIT = (65, 215, 100)
PLAYER = (65, 155, 255)
HUD = (8, 10, 15)
HEALTH_BRIGHT = (255, 225, 75)
HEALTH_DARK = (70, 60, 30)


@dataclass(frozen=True)
class Config:
    width: int = 64
    height: int = 64
    tile_size: int = 4
    hud_height: int = 4
    max_health: int = 8
    wall_count: int = 36
    hazard_count: int = 18
    max_steps: int = 256

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            minimum = 0 if field.name in ("wall_count", "hazard_count") else 1
            if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
                raise ValueError(f"{field.name} must be an integer >= {minimum}")
        if self.hud_height >= self.height:
            raise ValueError("hud_height must leave room for the world")
        if self.width % self.tile_size or (self.height - self.hud_height) % self.tile_size:
            raise ValueError("width and height minus hud_height must be divisible by tile_size")
        if self.max_health > self.width:
            raise ValueError("max_health must fit in the HUD (max_health <= width)")
        cells = self.columns * self.rows
        if cells < 2 or self.wall_count + self.hazard_count > cells - 2:
            raise ValueError("the world must have at least two cells free of walls and hazards")

    @property
    def columns(self):
        return self.width // self.tile_size

    @property
    def rows(self):
        return (self.height - self.hud_height) // self.tile_size


class EscapeEnv:
    """Call reset before stepping. Each returned observation and info is a snapshot."""

    def __init__(self, config: Config | None = None):
        self.config = config if config is not None else Config()
        self._rng = np.random.default_rng()
        self._ready = False

    def reset(self, seed=None):
        """Start a new episode; a seed restarts the environment's own RNG stream."""
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        c = self.config
        cells = [(x, y) for y in range(c.rows) for x in range(c.columns)]
        self.player = cells[int(self._rng.integers(len(cells)))]
        # Reserve a shuffled Manhattan path. Restrict distance so even dense
        # configurations have room for exact obstacle counts and a timely win.
        max_distance = min(c.max_steps, len(cells) - c.wall_count - c.hazard_count - 1)
        exits = [p for p in cells if 0 < self._distance(p, self.player) <= max_distance]
        self.exit = exits[int(self._rng.integers(len(exits)))]
        x, y = self.player
        ex, ey = self.exit
        moves = ([(1 if ex > x else -1, 0)] * abs(ex - x)
                 + [(0, 1 if ey > y else -1)] * abs(ey - y))
        self._rng.shuffle(moves)
        route = {self.player}
        for dx, dy in moves:
            x, y = x + dx, y + dy
            route.add((x, y))
        available = [p for p in cells if p not in route]
        indices = self._rng.choice(len(available), c.wall_count + c.hazard_count, replace=False)
        obstacles = [available[int(i)] for i in indices]
        self.walls = set(obstacles[:c.wall_count])
        self.hazards = set(obstacles[c.wall_count:])
        self.health_bar = (int(self._rng.integers(c.width - c.max_health + 1)),
                           int(self._rng.integers(c.hud_height)))
        self.health = c.max_health
        self.steps = 0
        self.terminated = self.truncated = False
        self._ready = True
        return self.render(), self._info()

    @staticmethod
    def _distance(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def step(self, action):
        """Return (RGB pixels, reward, terminated, truncated, diagnostic info)."""
        self._require_reset()
        if self.terminated or self.truncated:
            raise RuntimeError("episode has ended; call reset before stepping again")
        if isinstance(action, bool) or not isinstance(action, Integral):
            raise ValueError("action must be an Action or an integer from 0 to 4")
        try:
            action = Action(action)
        except ValueError as exc:
            raise ValueError("action must be an Action or an integer from 0 to 4") from exc
        dx, dy = DELTAS[action]
        target = (self.player[0] + dx, self.player[1] + dy)
        c = self.config
        if (0 <= target[0] < c.columns and 0 <= target[1] < c.rows
                and target not in self.walls):
            self.player = target
        self.steps += 1
        if self.player in self.hazards:
            self.health -= 1
        self.terminated = self.health == 0 or self.player == self.exit
        # Success/death on the final allowed action takes precedence over timeout.
        self.truncated = self.steps >= c.max_steps and not self.terminated
        reward = -1 if self.health == 0 else (1 if self.player == self.exit else 0)
        return self.render(), reward, self.terminated, self.truncated, self._info()

    def render(self):
        """Return a fresh uint8 (height, width, 3) array; no Pygame is needed."""
        self._require_reset()
        c = self.config
        image = np.empty((c.height, c.width, 3), dtype=np.uint8)
        image[:] = BACKGROUND
        image[:c.hud_height] = HUD

        def tile(position, color):
            x, y = position
            left, top = x * c.tile_size, c.hud_height + y * c.tile_size
            image[top:top + c.tile_size, left:left + c.tile_size] = color

        for position in self.walls:
            tile(position, WALL)
        for position in self.hazards:
            tile(position, HAZARD)
        tile(self.exit, EXIT)
        tile(self.player, PLAYER)
        x, y = self.health_bar
        image[y, x:x + c.max_health] = HEALTH_DARK
        image[y, x:x + self.health] = HEALTH_BRIGHT
        return image

    def _require_reset(self):
        if not self._ready:
            raise RuntimeError("call reset before using the environment")

    def _info(self):
        status = ("death" if self.health == 0 else "success" if self.player == self.exit
                  else "time_limit" if self.truncated else "playing")
        return {"health": self.health, "player": self.player, "exit": self.exit,
                "walls": tuple(sorted(self.walls)), "hazards": tuple(sorted(self.hazards)),
                "steps": self.steps, "health_bar": self.health_bar, "status": status}
