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

    # ---- task-agent episode execution ----
    # "per_probe": one constrained claude -p call per probe (simple; high overhead).
    # "single_session": run a whole episode (all probes + guess for ONE world) as a
    #   single claude -p session with the probe channel exposed as a narrow stdio-MCP
    #   tool, so the ~31k-token system-prompt overhead is paid once per world instead
    #   of once per probe. Default per_probe so the deterministic mock tests are
    #   untouched; real runners pass single_session.
    episode_mode: str = field(default_factory=lambda: _env("HTA_EPISODE_MODE", "per_probe"))
    episode_allowed_tools: Tuple[str, ...] = (
        "mcp__probe__probe", "mcp__probe__remaining", "mcp__probe__submit_guess")
    episode_turn_buffer: int = 8  # max_turns = max_probes + buffer (probe+read+guess+retries)

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

    # ---- meta-agent sandbox (production-grade airgap; see CONTAINERIZATION.md) ----
    # "none":   run the meta agent's claude -p in-process; airgapped only by denying
    #           Bash (the lighter mitigation). Default, so mock/tests are unchanged.
    # "docker": run claude -p INSIDE an ephemeral container that holds no host FS, no
    #           .env, and no world source; copy the child workspace in, edit, extract
    #           the result, destroy the container. Fails CLOSED if Docker is
    #           unavailable -- a security boundary must not silently downgrade.
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
    # Credentials forwarded host->container as ENV (never mounted files): with Bash
    # denied the model has no tool to read its own process env, so the token cannot be
    # exfiltrated through Edit/Read/Write -- whereas a mounted credential file could.
    sandbox_auth_env: Tuple[str, ...] = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")
    # Opt-in (weaker) fallback for subscription auth stored on disk: mount the claude
    # config dir read-only. Off by default; the env token above is preferred.
    sandbox_mount_claude_config: bool = field(
        default_factory=lambda: _env("HTA_SANDBOX_MOUNT_CLAUDE_CONFIG", "0") == "1")
    sandbox_claude_config_dir: str = field(
        default_factory=lambda: _env("HTA_SANDBOX_CLAUDE_CONFIG_DIR",
                                     os.path.expanduser("~/.claude")))

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
