"""Separate online setup from offline listing, play, and verification."""

import argparse
import sys

import requests

from .runtime import list_games, load_game


def main():
    parser = argparse.ArgumentParser(description="Run official public ARC-AGI-3 games locally.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list downloaded games (offline)")
    commands.add_parser("catalogue", help="list public games accessible through the official API (online)")
    download = commands.add_parser("download", help="download one public game via the official Toolkit (online)")
    download.add_argument("game_id", nargs="?", default="ls20")
    play = commands.add_parser("play", help="play a downloaded game (offline)")
    play.add_argument("game_id", nargs="?", default="ls20")
    play.add_argument("--scale", type=int, default=8, help="integer display enlargement; observations stay native")
    play.add_argument("--seed", type=int, default=0)
    verify = commands.add_parser("verify", help="check an actual downloaded game with all network connections blocked")
    verify.add_argument("game_id", nargs="?", default="ls20")
    args = parser.parse_args()
    try:
        if args.command in ("list", "catalogue"):
            if args.command == "catalogue":
                from .download import catalogue
                games = catalogue()
            else:
                games = list_games()
            for game in games:
                print(f"{game.game_id}\t{game.title or ''}")
            if not games:
                print("No games downloaded. Online setup: python -m arc_local download ls20")
        elif args.command == "download":
            from .download import download_game
            env = download_game(args.game_id)
            print(f"Downloaded and loaded offline: {env.info.game_id}")
        elif args.command == "verify":
            from .verify import verify_game
            verify_game(args.game_id)
        else:
            from .viewer import Viewer
            Viewer(load_game(args.game_id, seed=args.seed), scale=args.scale).run()
    except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
