"""Local access to official ARC-AGI-3 games; no observation or rule adapters."""

from .runtime import ENVIRONMENTS_DIR, list_games, load_game

__all__ = ["ENVIRONMENTS_DIR", "list_games", "load_game"]
