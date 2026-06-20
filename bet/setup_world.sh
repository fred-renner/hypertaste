#!/usr/bin/env bash
# Fetch the borrowed world (DiscoveryWorld, Ai2 2024) into bet/discoveryworld
# and install its runtime deps. The checkout is gitignored -- borrowed, not
# vendored. dw_world.py imports it from here (or from $BET_DW_PATH).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/discoveryworld"

if [ ! -d "$DEST/discoveryworld" ]; then
  echo "[setup] cloning DiscoveryWorld -> $DEST"
  git clone --depth 1 https://github.com/allenai/discoveryworld.git "$DEST"
else
  echo "[setup] DiscoveryWorld already present at $DEST"
fi

echo "[setup] installing runtime deps (pygame pathfinding psutil numpy termcolor tiktoken)"
pip install -q pygame pathfinding psutil numpy termcolor tiktoken

echo "[setup] smoke test (headless load)"
SDL_VIDEODRIVER=dummy PYTHONPATH="$DEST" python3 - <<'PY'
from discoveryworld.DiscoveryWorldAPI import DiscoveryWorldAPI
api = DiscoveryWorldAPI(threadID=99)
ok = api.loadScenario(scenarioName="Proteomics", difficultyStr="Normal", randomSeed=0, numUserAgents=1)
assert ok, "loadScenario failed"
print("[setup] OK -- DiscoveryWorld loads headless")
PY
echo "[setup] done."
