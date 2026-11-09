"""Explicit offline loading through the official Toolkit."""

import logging
import os
from pathlib import Path

from arc_agi import Arcade, LocalEnvironmentWrapper, OperationMode

ROOT = Path(__file__).resolve().parent
ENVIRONMENTS_DIR = ROOT / "environment_files"
OFFICIAL_API = "https://three.arcprize.org"

# The upstream INFO log includes anonymous API keys. Never emit those logs.
LOGGER = logging.getLogger("arc_local.toolkit")
LOGGER.setLevel(logging.WARNING)
LOGGER.propagate = False
if not LOGGER.handlers:
    LOGGER.addHandler(logging.StreamHandler())


def make_arcade(environments_dir=ENVIRONMENTS_DIR, *, download=False):
    """Use OFFLINE by default. Only the explicit download path can use NORMAL."""
    mode = os.getenv("OPERATION_MODE", "").strip().lower()
    # Upstream lets COMPETITION override even an explicit OFFLINE argument.
    # Fail before constructing Arcade, rather than accidentally contacting an API.
    if mode == "competition" or (download and mode not in ("", "normal")):
        raise RuntimeError("Unset OPERATION_MODE before using arc_local; this integration runs games locally.")
    if download and os.getenv("ARC_BASE_URL", OFFICIAL_API).rstrip("/") != OFFICIAL_API:
        raise RuntimeError("Unset ARC_BASE_URL to download from the official ARC Prize service.")
    return Arcade(
        operation_mode=OperationMode.NORMAL if download else OperationMode.OFFLINE,
        environments_dir=str(Path(environments_dir).resolve()),
        recordings_dir=str(ROOT / ".runtime" / "recordings"),
        arc_base_url=OFFICIAL_API,
        logger=LOGGER,
    )


def list_games(environments_dir=ENVIRONMENTS_DIR):
    """List complete local game installations, without fetching a catalogue."""
    games = make_arcade(environments_dir).get_environments()
    return sorted(
        [game for game in games if game.local_dir and any(
            (Path(game.local_dir) / name).is_file()
            for name in (f"{game.class_name}.py", f"{game.class_name.lower()}.py")
        )],
        key=lambda game: game.game_id,
    )


def load_game(game_id="ls20", *, seed=0, environments_dir=ENVIRONMENTS_DIR):
    """Return the official local wrapper, with its untouched FrameDataRaw API."""
    available = list_games(environments_dir)
    matches = [game for game in available if game.game_id == game_id
               or ("-" not in game_id and game.game_id.split("-", 1)[0] == game_id)]
    if not matches:
        raise FileNotFoundError(
            f"No downloaded game {game_id!r}. First run: python -m arc_local download {game_id}"
        )
    # Pin the selected version, rather than letting an incomplete download win.
    chosen = max(matches, key=lambda game: game.date_downloaded)
    env = make_arcade(environments_dir).make(chosen.game_id, seed=seed)
    if not isinstance(env, LocalEnvironmentWrapper) or env.observation_space is None:
        raise RuntimeError(f"The official Toolkit could not load {chosen.game_id}.")
    return env
