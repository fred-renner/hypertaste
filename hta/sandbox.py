"""Production-grade airgap for the self-modifying META AGENT (TODO 3).

The meta agent is the one untrusted, self-modifying actor in the system: it runs as
an agentic `claude -p` with Edit/Read/Write tools. Denying it Bash (DirectSandbox)
shrinks the blast radius but is NOT a hard boundary -- the Read tool can still read
absolute host paths, so host secrets and the world source are only a path away.

`DockerSandbox` makes it a hard boundary: claude runs INSIDE an ephemeral container
that simply does not contain the host filesystem, the `.env`, or `hta/world/*` (where
the hidden rule lives). The child workspace is copied IN, edited, the result copied
OUT, and the container destroyed -- edit -> extract -> reset, mirroring HyperAgents'
`docker_utils.py` + `gl_utils.py` in-container diff cycle (see REFERENCE.md).

Open questions from HANDOFF.md TODO 3, resolved here (full rationale in
CONTAINERIZATION.md):
  * "run claude inside, or mount the workspace and run claude on the host?" -> run it
    INSIDE the container. That is the only way to actually contain Edit/Read/Write: if
    claude ran on the host, its Read tool would see the host filesystem regardless of
    any mount tricks.
  * Credentials are passed as ENV, never mounted files: with Bash denied the model has
    no tool to read its own process environment, so the token cannot be exfiltrated
    through Edit/Read/Write (a mounted credential file, by contrast, is Read-able).
  * Network is configurable; production restricts egress to the Anthropic API.
  * Fails CLOSED: if `sandbox=docker` but Docker is unavailable we raise rather than
    silently downgrade the airgap.

All Docker invocations go through the module-level `_run` seam, so the orchestration
(create -> cp in -> start -> cp out -> rm) and the diff/apply are fully testable
without a running daemon (tests/test_sandbox.py).
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from typing import List, Optional

from . import llm
from .config import Config

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCKERFILE = os.path.join(_REPO_ROOT, "docker", "Dockerfile.agent")
_DOCKER_CONTEXT = os.path.join(_REPO_ROOT, "docker")
_WORKSPACE = "/workspace"
_SKIP = ("__pycache__", ".git", ".pytest_cache")


# ---------------------------------------------------------------------------
# subprocess seam (monkeypatched in tests so the orchestration is daemon-free)
# ---------------------------------------------------------------------------
def _run(cmd: List[str], timeout: Optional[int] = None, check: bool = False):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd[:3])} ... "
                           f"{((proc.stderr or proc.stdout) or '')[:200]}")
    return proc


# ---------------------------------------------------------------------------
# Docker preflight
# ---------------------------------------------------------------------------
def docker_available(cfg: Config) -> bool:
    """True iff the docker CLI is on PATH AND its daemon is reachable."""
    if shutil.which(cfg.sandbox_docker_bin) is None:
        return False
    try:
        proc = _run([cfg.sandbox_docker_bin, "version", "--format", "{{.Server.Version}}"],
                    timeout=20)
    except Exception:
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def image_exists(cfg: Config) -> bool:
    try:
        proc = _run([cfg.sandbox_docker_bin, "image", "inspect", cfg.sandbox_image], timeout=30)
    except Exception:
        return False
    return proc.returncode == 0


def build_image(cfg: Config, log=print) -> None:
    log(f"  [docker] building agent image {cfg.sandbox_image} ...")
    _run([cfg.sandbox_docker_bin, "build", "-t", cfg.sandbox_image,
          "-f", _DOCKERFILE, _DOCKER_CONTEXT], timeout=cfg.call_timeout_s * 6, check=True)


# ---------------------------------------------------------------------------
# Workspace diff/apply (the "extract" step). Pure; unit-tested without a daemon.
# ---------------------------------------------------------------------------
def apply_workspace_changes(src_dir: str, dst_dir: str, log=print) -> List[str]:
    """Copy files that were added/modified in `src_dir` (the container's resulting
    /workspace) back into `dst_dir` (the host node dir). Returns the changed relative
    paths. Skips caches; does not delete (the meta agent edits, it does not prune)."""
    changed: List[str] = []
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP]
        for fn in files:
            sp = os.path.join(root, fn)
            rel = os.path.relpath(sp, src_dir)
            dp = os.path.join(dst_dir, rel)
            if not _same_file(sp, dp):
                os.makedirs(os.path.dirname(dp) or ".", exist_ok=True)
                shutil.copy2(sp, dp)
                changed.append(rel)
    return sorted(changed)


def _same_file(a: str, b: str) -> bool:
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Sandboxes
# ---------------------------------------------------------------------------
class DirectSandbox:
    """Soft airgap (current default): claude -p agentic in-process, Bash denied.
    Identical behavior to the pre-TODO-3 code path."""

    name = "none"

    def run_meta_edit(self, child_dir: str, instruction: str, cfg: Config, log=print) -> dict:
        return llm.agentic(instruction, workdir=child_dir, model=cfg.meta_model,
                           allowed_tools=cfg.meta_allowed_tools,
                           max_turns=cfg.meta_max_turns, role="meta", cfg=cfg)


class DockerSandbox:
    """Hard airgap: claude -p runs inside an ephemeral, host-isolated container.

    Cycle per child: create (isolated) -> cp workspace IN -> start (edit) ->
    cp workspace OUT -> apply diff to the host node dir -> rm container (reset)."""

    name = "docker"

    def _preflight(self, cfg: Config, log) -> None:
        if not docker_available(cfg):
            raise RuntimeError(
                "sandbox=docker but Docker is unavailable (CLI missing or daemon down). "
                "A security boundary must not silently downgrade: start Docker, or run "
                "with --sandbox none to accept the soft (Bash-denied) airgap.")
        if not image_exists(cfg):
            if cfg.sandbox_autobuild:
                build_image(cfg, log=log)
            else:
                raise RuntimeError(
                    f"agent image {cfg.sandbox_image!r} not found. Build it once with "
                    f"`scripts/build_agent_image.sh` (or set HTA_SANDBOX_AUTOBUILD=1).")

    def _create_cmd(self, cfg: Config, name: str, argv: List[str]) -> List[str]:
        """`docker create` for an isolated, resource-limited, non-root container.
        Note what is ABSENT: no bind mount of the repo, `hta/world/*`, `.env`, or any
        host path -- the workspace is copied in afterward, so the container's only view
        of host data is the child program itself."""
        cmd = [cfg.sandbox_docker_bin, "create", "--name", name,
               "--workdir", _WORKSPACE,
               "--network", cfg.sandbox_network,
               "--memory", cfg.sandbox_memory,
               "--cpus", str(cfg.sandbox_cpus),
               "--pids-limit", str(cfg.sandbox_pids),
               "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges"]
        for var in cfg.sandbox_auth_env:
            if os.environ.get(var):
                cmd += ["-e", f"{var}={os.environ[var]}"]
        if cfg.sandbox_mount_claude_config and cfg.sandbox_claude_config_dir:
            cmd += ["-v", f"{cfg.sandbox_claude_config_dir}:/home/agent/.claude:ro"]
        cmd.append(cfg.sandbox_image)
        cmd += argv
        return cmd

    def run_meta_edit(self, child_dir: str, instruction: str, cfg: Config, log=print) -> dict:
        self._preflight(cfg, log)
        argv = llm.agentic_argv(instruction, cfg.meta_model,
                                cfg.meta_allowed_tools, cfg.meta_max_turns)
        name = "hta_meta_" + uuid.uuid4().hex[:12]
        docker = cfg.sandbox_docker_bin
        proc = None
        changed: List[str] = []
        try:
            _run(self._create_cmd(cfg, name, argv), timeout=60, check=True)
            _run([docker, "cp", os.path.join(child_dir, "."), f"{name}:{_WORKSPACE}"],
                 timeout=120, check=True)
            proc = _run([docker, "start", "--attach", name],
                        timeout=cfg.call_timeout_s * 3, check=False)
            with tempfile.TemporaryDirectory() as result_dir:
                _run([docker, "cp", f"{name}:{_WORKSPACE}/.", result_dir],
                     timeout=120, check=True)
                changed = apply_workspace_changes(result_dir, child_dir, log=log)
        finally:
            _run([docker, "rm", "-f", name], timeout=60, check=False)
        res = llm.agentic_result_from_stdout(proc.stdout if proc else "", role="meta",
                                             model=cfg.meta_model)
        log(f"  [docker] edited in container; changed={changed or 'none'}")
        return res


_SANDBOXES = {"none": DirectSandbox, "docker": DockerSandbox}


def get_sandbox(cfg: Config):
    """Factory: pick the sandbox strategy for the meta agent from `cfg.sandbox`."""
    cls = _SANDBOXES.get(cfg.sandbox)
    if cls is None:
        raise ValueError(f"unknown sandbox {cfg.sandbox!r}; choose one of {sorted(_SANDBOXES)}")
    return cls()
