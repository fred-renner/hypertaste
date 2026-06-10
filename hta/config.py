"""Central configuration: model assignment, knobs, paths.

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

    # ---- Chapter-2 option-B harness (the model-orchestrated player) ----
    # The confined toolsets (the airgap): the playbook-driven TOP gets the full orchestration
    # allowlist; a spawned WORKER is confined to probe/remaining and sees only its task + budget.
    # No Bash/Read/Edit/Write/Web ever (episode() also denies them belt-and-suspenders).
    top_allowed_tools: Tuple[str, ...] = (
        "mcp__probe__probe", "mcp__probe__remaining", "mcp__probe__world_map",
        "mcp__probe__mem_read", "mcp__probe__mem_patch", "mcp__probe__submit_map",
        "mcp__probe__spawn")
    worker_allowed_tools: Tuple[str, ...] = ("mcp__probe__probe", "mcp__probe__remaining")
    # The top reasons, spawns, keeps a scratchpad, then submits — the budget (probes) binds, not
    # turns, so give generous turn headroom (Gotchas: "probes, not turns, bind").
    top_max_turns: int = 40

    # ---- world ----
    # Which build-screened spec the loop trains on: "anchor" (the canary, default) or "hidden"
    # (the Pass-3 hidden-map family, hta/ch2/hidden_map.py). The canary stays default until the
    # new world replaces it (PLAN.md -> "The staged passes").
    world_kind: str = field(default_factory=lambda: _env("HTA_WORLD_KIND", "anchor"))

    # ---- evaluation ----
    n_train_worlds: int = 4
    n_transfer_worlds: int = 4  # frozen held-out worlds -> measures generalization
    # Episodes are independent claude -p subprocesses, so the per-world eval is run
    # concurrently (the dominant wall-clock cost was serial episodes). Caps the number
    # of simultaneous claude -p sessions. 1 = serial (mock/tests path is always serial
    # and deterministic regardless of this value).
    eval_concurrency: int = 4
    # Episodes are stochastic (weak Haiku task model) and a world set is small, so a
    # single pass is noisy: in the TODO-1 run the SAME seed program scored 0.76/0.43/0.58
    # across iterations. Re-running each world's episode and averaging shrinks that
    # variance so a genuinely-better child is not lost to chance. 1 = no repeats (keeps
    # the deterministic mock pipeline untouched); real runs raise it (cost scales x N).
    eval_repeats: int = 1

    # ---- Solomonoff/MDL prior on the agent program ----
    # A small fitness-per-bit regularizer applied at SELECTION time (not a term in the
    # world-score, not a hard cap): among comparable fitness, prefer the shorter program --
    # the generality prior (a shorter program explaining more worlds captured a real
    # regularity, not the curriculum). Held-out fitness guards against winning by deleting
    # capability. 0 disables it. See hta/archive.py and taste.program_description_length.
    mdl_lambda: float = 0.05

    # ---- meta agent (airgap: NO Bash tool, edits code only) ----
    meta_allowed_tools: Tuple[str, ...] = ("Edit", "Read", "Write")
    # The Read -> diagnose -> Edit loop (often across solver.py + meta_strategy.md +
    # episode_prompt.md) does not fit in a tight budget: the TODO-1 run hit the cap
    # (turns=13 at budget 12) every iteration and edits were cut off mid-revision. 40
    # gives the agent room to finish a multi-file edit cleanly.
    meta_max_turns: int = 40

    # ---- parent selection (open-ended search over the archive) ----
    # "weighted": quality x novelty, mirroring HyperAgents' score_child_prop -- a sigmoid
    #   of fitness (favors better stepping stones) times an inverse child-count penalty
    #   (favors under-explored nodes), so lineage compounds toward good recent children
    #   instead of re-branching the seed every iteration (the TODO-1 lineage stall).
    # "random": uniform over valid parents (the prior behavior; kept for reproducibility).
    parent_selection: str = "weighted"
    parent_novelty_scale: float = 2.0     # smaller -> child-count penalty bites sooner
    parent_quality_sharpness: float = 10.0  # larger -> stronger pull toward higher fitness

    # ---- meta-agent sandbox (the WORLD airgap for the self-modifying meta agent) ----
    # "none":   run the meta agent's claude -p in-process; airgapped only by denying
    #           Bash (the lighter mitigation). Default, so mock/tests are unchanged.
    # "docker": run claude -p INSIDE an ephemeral container that holds NO repo and NO
    #           world source (hta/world/*); copy the child workspace in, edit, extract
    #           the result, destroy the container. Fails CLOSED if Docker is
    #           unavailable -- a security boundary must not silently downgrade.
    # We airgap the WORLD, not the infra: the container authenticates on the host's
    # subscription (mounted ~/.claude, below). The token is not the secret -- the
    # hidden rule + scorer are -- so we keep auth simple instead of hiding it.
    sandbox: str = field(default_factory=lambda: _env("HTA_SANDBOX", "none"))
    sandbox_image: str = field(
        default_factory=lambda: _env("HTA_SANDBOX_IMAGE", "hypertaste-agent:latest"))
    sandbox_network: str = field(default_factory=lambda: _env("HTA_SANDBOX_NETWORK", "bridge"))
    sandbox_memory: str = field(default_factory=lambda: _env("HTA_SANDBOX_MEMORY", "2g"))
    sandbox_cpus: str = field(default_factory=lambda: _env("HTA_SANDBOX_CPUS", "2"))
    sandbox_pids: int = 256
    sandbox_autobuild: bool = field(
        default_factory=lambda: _env("HTA_SANDBOX_AUTOBUILD", "0") == "1")
    sandbox_docker_bin: str = field(default_factory=lambda: _env("HTA_DOCKER_BIN", "docker"))
    # Default auth path: mount the host claude config dir read-only so the in-container
    # claude runs on the host's subscription. The world airgap is unaffected -- only
    # ~/.claude is mounted, never the repo or hta/world/*.
    sandbox_mount_claude_config: bool = field(
        default_factory=lambda: _env("HTA_SANDBOX_MOUNT_CLAUDE_CONFIG", "1") == "1")
    sandbox_claude_config_dir: str = field(
        default_factory=lambda: _env("HTA_SANDBOX_CLAUDE_CONFIG_DIR",
                                     os.path.expanduser("~/.claude")))
    # Also forwarded as ENV when present, e.g. an API key or OAuth token in the
    # environment (an alternative to the mount above; both may be set).
    sandbox_auth_env: Tuple[str, ...] = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")

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
        c.n_train_worlds = 2
        c.n_transfer_worlds = 2
        return c
