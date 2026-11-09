# Official sources and attribution

ARC-AGI-3, its Toolkit, engine, and public games are provided by ARC Prize
Foundation. This repository adds local download/loading commands and a viewer;
it does not claim authorship of official environments.

Sources inspected on 2026-11-09:

- [Toolkit](https://github.com/arcprize/ARC-AGI), version `0.9.9`, source commit
  `f12822c4d550121c35a275008d964afbbed47d2f`.
- [ARCEngine](https://github.com/arcprize/ARCEngine), version `0.9.3`, source commit
  `b495c6acaf253c9681cd7b75c4299d352e9ce6f8`.
- [Documentation](https://docs.arcprize.org/), including
  [local vs online](https://docs.arcprize.org/local-vs-online),
  [editing games](https://docs.arcprize.org/edit_games),
  [actions](https://docs.arcprize.org/actions), and
  [available games](https://docs.arcprize.org/available-games).
  The documentation website was blocked by this cloud's network policy; these
  exact pages were read in ARC Prize's [official documentation repository](https://github.com/arcprize/docs)
  at commit `6956cde0c84b9b077d31ae98e5a9a243622a2553`.

The Toolkit and engine have MIT licenses, copied unchanged into
[`licenses/ARC-AGI.txt`](licenses/ARC-AGI.txt) and
[`licenses/ARCEngine.txt`](licenses/ARCEngine.txt). They are installed as official
PyPI packages, rather than copied or modified here.

The documented download path is `Arcade(operation_mode=OperationMode.NORMAL,
environments_dir=...).make(game_id)`. It retrieves a public game's source and
metadata from `https://three.arcprize.org/api/games/...`. Subsequent execution
uses `OperationMode.OFFLINE` and does not use the gameplay API.

Downloaded game files retain their original source, metadata, and any embedded
copyright/license notices. A separate `provenance.json` records the official
source URL, package versions, and SHA-256 hashes without credentials. Nothing
here assigns a new license to upstream games. Preserve any supplied notices and
applicable ARC Prize terms when sharing additional downloads.

No official game files are currently bundled: access to the download service
was denied by the cloud proxy before an anonymous key or source was obtained.
The Toolkit's synthetic test games and ARCEngine demo mazes were not substituted.
