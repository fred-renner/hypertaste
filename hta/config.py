"""Central configuration: model assignment, knobs, fitness weights, paths.

Model assignment lives here (and can be overridden by env vars), so "which model
runs which role" is a one-stop decision:

    HTA_TASK_MODEL   task agent  (probing + guessing)        default: haiku
    HTA_META_MODEL   meta agent  (self-modification)         default: opus
    HTA_WORLD_MODEL  world-smith (curriculum generation)     default: opus
    HTA_BACKEND      "real" (claude -p) | "mock" (offline)   default: mock
"""

import os
from dataclasses import dataclass, field
from typing import Tuple


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    # ---- backend ----
    backend: str = field(default_factory=lambda: _env("HTA_BACKEND", "mock"))

    # ---- model assignment (claude -p --model aliases) ----
    task_model: str = field(default_factory=lambda: _env("HTA_TASK_MODEL", "haiku"))
    meta_model: str = field(default_factory=lambda: _env("HTA_META_MODEL", "opus"))
    world_model: str = field(default_factory=lambda: _env("HTA_WORLD_MODEL", "opus"))

    # ---- WILT knobs ----
    max_probes: int = 30  # classic WILT allows up to 30 test cases

    # ---- evaluation ----
    n_train_worlds: int = 4
    n_transfer_worlds: int = 4  # frozen held-out worlds -> measures generalization

    # ---- fitness weights (sum ~1.0); "solve the world" dominates, taste shapes ----
    w_solve: float = 0.50     # exact rule recovery (Occam-correct)
    w_approx: float = 0.20    # agreement fraction with hidden rule
    w_info: float = 0.15      # avg hypothesis-space reduction per probe
    w_novelty: float = 0.10   # 1 - probe reuse rate (anti doom-loop)
    w_occam: float = 0.05     # simplicity of final guess

    # ---- meta agent (airgap: NO Bash tool, edits code only) ----
    meta_allowed_tools: Tuple[str, ...] = ("Edit", "Read", "Write")
    meta_max_turns: int = 30

    # ---- paths ----
    out_dir: str = "outputs"

    # ---- timeouts ----
    call_timeout_s: int = 180

    @property
    def archive_dir(self) -> str:
        return os.path.join(self.out_dir, "archive")

    @classmethod
    def testing(cls) -> "Config":
        """Tiny, cheap profile for verifying the pipeline end-to-end."""
        c = cls()
        c.max_probes = 6
        c.n_train_worlds = 2
        c.n_transfer_worlds = 2
        return c
