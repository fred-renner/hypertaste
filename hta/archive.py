"""Archive of hyperagents: the open-ended store of stepping stones.

Each node is a directory holding the editable program (solver.py + meta_strategy.md)
and a node.json with its evaluation summary. Parent selection keeps the search open
(it does not always greedily pick the current best) so the archive can branch from
non-greedy stepping stones. The default policy is HyperAgents' score_child_prop shape:
sample a parent with probability proportional to quality (a sigmoid of fitness) times
novelty (an inverse child-count penalty). That biases toward good, under-explored
children so lineage compounds across iterations -- the TODO-1 run's pure-random policy
re-selected the seed all three times and improvements never accumulated. A "random"
policy (uniform over valid parents) is retained for reproducibility.
"""

import json
import math
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

    def children_count(self, genid: int) -> int:
        """How many archive nodes were branched from this one (its fan-out)."""
        return sum(1 for g in self.genids() if self._meta(g).get("parent") == genid)

    def _selection_weights(self, candidates, novelty_scale, sharpness):
        """quality x novelty per candidate (HyperAgents score_child_prop shape).

        quality = sigmoid(sharpness * (fitness - mean_fitness)) -- centered on the
        archive's mean so it favors above-average stepping stones regardless of the
        absolute fitness scale. The seed (and any not-yet-scored node) is imputed the
        mean, so it stays selectable early but yields to proven children once they exist.
        novelty = exp(-(children_count / novelty_scale)^3) -- a node already branched many
        times is damped, pushing the search toward fresh nodes."""
        scores = [self.fitness(g) for g in candidates]
        known = [s for s in scores if s is not None]
        center = (sum(known) / len(known)) if known else 0.5
        weights = []
        for g, s in zip(candidates, scores):
            s = center if s is None else s
            quality = 1.0 / (1.0 + math.exp(-sharpness * (s - center)))
            novelty = math.exp(-((self.children_count(g) / novelty_scale) ** 3))
            weights.append(max(quality * novelty, 1e-9))
        return weights

    def select_parent(self, rng: Optional[random.Random] = None, *,
                      policy: str = "weighted", novelty_scale: float = 2.0,
                      sharpness: float = 10.0) -> int:
        rng = rng or random
        candidates = self.valid_parents()
        if not candidates:
            raise ValueError("archive has no valid parents")
        if policy == "random" or len(candidates) == 1:
            return rng.choice(candidates)
        weights = self._selection_weights(candidates, novelty_scale, sharpness)
        return rng.choices(candidates, weights=weights, k=1)[0]

    def best(self) -> Optional[int]:
        scored = [(self.fitness(g), g) for g in self.genids() if self.fitness(g) is not None]
        if not scored:
            return None
        return max(scored)[1]

    def summary_table(self) -> List[dict]:
        return [self._meta(g) for g in self.genids()]
