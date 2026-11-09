"""Online setup only: use Arcade.make's documented public-game download path."""

import hashlib
import importlib.metadata
import json
import re
import shutil
import tempfile
from pathlib import Path

from .runtime import ENVIRONMENTS_DIR, OFFICIAL_API, load_game, make_arcade


def catalogue():
    """Return the official accessible catalogue; do not download any game source."""
    with tempfile.TemporaryDirectory(prefix="arc-catalogue-") as temporary:
        games = make_arcade(temporary, download=True).get_environments()
    if not games:
        raise RuntimeError("No public catalogue received. Check network access and ARC_API_KEY permissions.")
    return sorted(games, key=lambda game: game.game_id)


def download_game(game_id="ls20", environments_dir=ENVIRONMENTS_DIR):
    if not re.fullmatch(r"[a-z0-9]{4}(?:-[A-Za-z0-9_]+)?", game_id):
        raise ValueError("Use a public catalogue game ID, such as ls20 or its full versioned ID.")
    target = Path(environments_dir).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    # A failed download must not leave metadata that looks like an installed game.
    with tempfile.TemporaryDirectory(prefix=".download-", dir=target.parent) as temporary:
        staging = Path(temporary)
        arc = make_arcade(staging, download=True)
        accessible = {game.game_id for game in arc.get_environments()}
        if not any(game == game_id or ("-" not in game_id and game.split("-", 1)[0] == game_id)
                   for game in accessible):
            raise RuntimeError(
                f"{game_id!r} is not in the accessible public catalogue. "
                "Use 'python -m arc_local catalogue'; additional public games may need ARC_API_KEY."
            )
        # NORMAL downloads source/metadata and executes the game locally. It does
        # not use ONLINE/COMPETITION or remote gameplay action endpoints.
        env = arc.make(game_id)
        if env is None or env.observation_space is None:
            raise RuntimeError(f"Official download/load of {game_id!r} failed; no game was installed.")
        source_dir = Path(env.info.local_dir).resolve()
        relative = source_dir.relative_to(staging)
        destination = target / relative
        if destination.exists():
            raise FileExistsError(f"Already downloaded: {destination}. Existing game files were preserved.")
        provenance = {
            "game_id": env.info.game_id,
            "download_method": "arc_agi.Arcade(OperationMode.NORMAL).make",
            "source_url": f"{OFFICIAL_API}/api/games/{env.info.game_id}/source",
            "packages": {name: importlib.metadata.version(name) for name in ("arc-agi", "arcengine")},
            "sha256": {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                       for file in sorted(source_dir.iterdir()) if file.is_file()},
        }
        # Source and metadata remain byte-for-byte as written by the Toolkit.
        (source_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_dir), str(destination))
    # Re-open using OFFLINE and the final path, never rely on the staging instance.
    return load_game(env.info.game_id, environments_dir=target)
