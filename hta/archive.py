"""Archive of hyperagents: the open-ended store of stepping stones.

Each node is a directory holding the editable program (solver.py + meta_strategy.md)
and a node.json with its evaluation summary. Parent selection keeps the search open
(random among valid parents, as in the DGM/HyperAgents reference) so the archive can
branch from non-greedy stepping stones, not just the current best.
"""

import json
import os
import random
import shutil
from typing import List, Optional


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return default


class Archive:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    # ---- layout ----
    def node_dir(self, genid: int) -> str:
        return os.path.join(self.root, f"gen_{genid:04d}")

    def _meta(self, genid: int) -> dict:
        return _read_json(os.path.join(self.node_dir(genid), "node.json"), {}) or {}

    def genids(self) -> List[int]:
        ids = []
        for name in os.listdir(self.root):
            if name.startswith("gen_") and os.path.isdir(os.path.join(self.root, name)):
                try:
                    ids.append(int(name[4:]))
                except ValueError:
                    pass
        return sorted(ids)

    def is_empty(self) -> bool:
        return len(self.genids()) == 0

    def next_genid(self) -> int:
        ids = self.genids()
        return (max(ids) + 1) if ids else 0

    # ---- creation ----
    def seed(self, seed_dir: str) -> int:
        """Create gen_0000 from a seed program directory."""
        genid = 0
        dst = self.node_dir(genid)
        if os.path.exists(dst):
            return genid
        shutil.copytree(seed_dir, dst)
        self._write_meta(genid, {"genid": genid, "parent": None, "valid": True,
                                 "fitness": None, "solved_train": None,
                                 "solved_transfer": None, "note": "seed"})
        return genid

    def add(self, genid: int, parent: int, summary: dict) -> None:
        meta = {"genid": genid, "parent": parent, "valid": summary.get("valid", True)}
        meta.update(summary)
        self._write_meta(genid, meta)

    def _write_meta(self, genid: int, meta: dict) -> None:
        with open(os.path.join(self.node_dir(genid), "node.json"), "w") as f:
            json.dump(meta, f, indent=2)

    # ---- queries ----
    def fitness(self, genid: int) -> Optional[float]:
        return self._meta(genid).get("fitness")

    def valid_parents(self) -> List[int]:
        out = []
        for g in self.genids():
            m = self._meta(g)
            if m.get("valid", True):
                out.append(g)
        return out

    def select_parent(self, rng: Optional[random.Random] = None) -> int:
        rng = rng or random
        candidates = self.valid_parents()
        if not candidates:
            raise ValueError("archive has no valid parents")
        return rng.choice(candidates)

    def best(self) -> Optional[int]:
        scored = [(self.fitness(g), g) for g in self.genids() if self.fitness(g) is not None]
        if not scored:
            return None
        return max(scored)[1]

    def summary_table(self) -> List[dict]:
        return [self._meta(g) for g in self.genids()]
