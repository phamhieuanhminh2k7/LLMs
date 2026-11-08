"""Pygame display and keyboard controls, separate from the simulation."""

import argparse
from dataclasses import fields

import pygame

from .environment import Action, Config, EscapeEnv


KEY_ACTIONS = {
    pygame.K_UP: Action.UP, pygame.K_w: Action.UP,
    pygame.K_DOWN: Action.DOWN, pygame.K_s: Action.DOWN,
    pygame.K_LEFT: Action.LEFT, pygame.K_a: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT, pygame.K_d: Action.RIGHT,
    pygame.K_SPACE: Action.WAIT,
}


def run(env: EscapeEnv, *, seed=None, scale=8):
    """Run until Escape/window close. Idle display frames never advance the world."""
    if not isinstance(scale, int) or isinstance(scale, bool) or scale < 1:
        raise ValueError("scale must be a positive integer")
    c = env.config
    pygame.display.init()
    try:
        window = pygame.display.set_mode((c.width * scale, c.height * scale), pygame.RESIZABLE)
        pygame.key.set_repeat()  # One action per key press, without automatic repeats.
        clock = pygame.time.Clock()
        observation, info = env.reset(seed=seed)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        observation, info = env.reset()
                    elif event.key in KEY_ACTIONS and not (env.terminated or env.truncated):
                        observation, _, _, _, info = env.step(KEY_ACTIONS[event.key])
            status = {"playing": "Reach the green exit",
                      "success": "SUCCESS! R to play again",
                      "death": "FAILURE: no health. R to retry",
                      "time_limit": "FAILURE: time limit. R to retry"}[info["status"]]
            pygame.display.set_caption(f"Pixel Escape | {status} | R reset | Esc quit")
            # Pygame arrays are (width, height, RGB); environment arrays are HWC.
            surface = pygame.surfarray.make_surface(observation.transpose(1, 0, 2))
            ratio = min(window.get_width() / c.width, window.get_height() / c.height)
            size = (max(1, int(c.width * ratio)), max(1, int(c.height * ratio)))
            enlarged = pygame.transform.scale(surface, size)  # Nearest neighbor.
            window.fill((0, 0, 0))
            window.blit(enlarged, ((window.get_width() - size[0]) // 2,
                                   (window.get_height() - size[1]) // 2))
            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Reach the green exit without losing all your health.")
    for field in fields(Config):
        parser.add_argument("--" + field.name.replace("_", "-"), type=int, default=field.default)
    parser.add_argument("--seed", type=int, help="reproduce the initial layout and subsequent resets")
    parser.add_argument("--scale", type=int, default=8, help="initial display enlargement (default: 8)")
    args = vars(parser.parse_args())
    seed, scale = args.pop("seed"), args.pop("scale")
    try:
        config = Config(**args)
        if scale < 1:
            raise ValueError("scale must be positive")
        if seed is not None and seed < 0:
            raise ValueError("seed must be nonnegative")
    except ValueError as exc:
        parser.error(str(exc))
    run(EscapeEnv(config), seed=seed, scale=scale)
