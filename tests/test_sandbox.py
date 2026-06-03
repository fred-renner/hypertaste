"""Sandbox / containerized-airgap tests (TODO 3).

The Docker path is exercised WITHOUT a running daemon: every docker invocation goes
through the `hta.sandbox._run` seam, which these tests monkeypatch. So we verify the
orchestration (create -> cp in -> start -> cp out -> rm), the diff/apply ("extract"),
the isolation flags, and the fail-closed preflight, all offline and for free.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from hta import llm, sandbox  # noqa: E402
from hta.config import Config  # noqa: E402


def _docker_cfg(**kw):
    cfg = Config()
    cfg.sandbox = "docker"
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------------------
# factory + DirectSandbox routing
# ---------------------------------------------------------------------------
def test_factory_routing():
    assert isinstance(sandbox.get_sandbox(Config()), sandbox.DirectSandbox)  # default none
    assert isinstance(sandbox.get_sandbox(_docker_cfg()), sandbox.DockerSandbox)
    with pytest.raises(ValueError):
        bad = Config()
        bad.sandbox = "qemu"
        sandbox.get_sandbox(bad)


def test_direct_sandbox_delegates_to_agentic(monkeypatch):
    seen = {}

    def fake_agentic(instruction, workdir, model, allowed_tools, max_turns, role, cfg):
        seen.update(dict(instruction=instruction, workdir=workdir, model=model,
                         allowed_tools=allowed_tools, max_turns=max_turns, role=role))
        return {"is_error": False, "result": "ok", "num_turns": 4, "cost_usd": 0.5}

    monkeypatch.setattr(llm, "agentic", fake_agentic)
    cfg = Config()  # sandbox=none
    res = sandbox.get_sandbox(cfg).run_meta_edit("/tmp/childX", "INSTR", cfg)
    assert res["num_turns"] == 4 and res["cost_usd"] == 0.5
    assert seen["workdir"] == "/tmp/childX" and seen["role"] == "meta"
    assert seen["allowed_tools"] == cfg.meta_allowed_tools
    assert "Bash" not in seen["allowed_tools"]  # airgap: never granted Bash


# ---------------------------------------------------------------------------
# diff/apply ("extract" step)
# ---------------------------------------------------------------------------
def test_apply_workspace_changes(tmp_path):
    src = tmp_path / "result"
    dst = tmp_path / "node"
    src.mkdir()
    dst.mkdir()
    # dst (host node) starts as the pristine workspace
    (dst / "solver.py").write_text("original\n")
    (dst / "meta_strategy.md").write_text("playbook\n")
    # src (container result) is the SAME except solver.py edited + a new file added
    (src / "solver.py").write_text("original\n# edited\n")
    (src / "meta_strategy.md").write_text("playbook\n")  # unchanged
    (src / "NOTES.md").write_text("new file\n")          # added
    cache = src / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_text("junk")                 # must be skipped

    changed = sandbox.apply_workspace_changes(str(src), str(dst))

    assert changed == ["NOTES.md", "solver.py"]          # sorted, unchanged file excluded
    assert (dst / "solver.py").read_text() == "original\n# edited\n"
    assert (dst / "NOTES.md").read_text() == "new file\n"
    assert not (dst / "__pycache__").exists()            # cache not propagated


# ---------------------------------------------------------------------------
# isolation flags in the `docker create` command
# ---------------------------------------------------------------------------
def test_docker_create_cmd_isolation(monkeypatch):
    # no auth env present -> no -e flags
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _docker_cfg(sandbox_network="none", sandbox_memory="1g",
                      sandbox_cpus="1", sandbox_pids=128,
                      sandbox_image="hypertaste-agent:test")
    argv = ["claude", "-p", "INSTR", "--model", "opus"]
    cmd = sandbox.DockerSandbox()._create_cmd(cfg, "hta_meta_abc", argv)
    joined = " ".join(cmd)

    assert cmd[:3] == ["docker", "create", "--name"]
    assert "--network none" in joined
    assert "--memory 1g" in joined
    assert "--cpus 1" in joined
    assert "--pids-limit 128" in joined
    assert "--cap-drop ALL" in joined
    assert "--security-opt no-new-privileges" in joined
    assert "--workdir /workspace" in joined
    # the image must come right before the agent argv
    img_i = cmd.index("hypertaste-agent:test")
    assert cmd[img_i + 1:] == argv
    # CRUCIAL: no host bind mount at all -> no path to host secrets or world source
    assert "-v" not in cmd
    assert "-e" not in cmd  # no credential env present in this case


def test_docker_create_cmd_forwards_present_auth_env_only(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "tok-123")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _docker_cfg()
    cmd = sandbox.DockerSandbox()._create_cmd(cfg, "hta_meta_abc", ["claude"])
    assert "CLAUDE_CODE_OAUTH_TOKEN=tok-123" in cmd
    assert not any("ANTHROPIC_API_KEY" in c for c in cmd)  # absent var not forwarded
    # credential travels as -e (env), never as a -v mounted file
    assert "-v" not in cmd


def test_docker_create_cmd_optional_config_mount(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = _docker_cfg(sandbox_mount_claude_config=True,
                      sandbox_claude_config_dir="/home/u/.claude")
    cmd = sandbox.DockerSandbox()._create_cmd(cfg, "n", ["claude"])
    assert "-v" in cmd
    assert "/home/u/.claude:/home/agent/.claude:ro" in cmd


# ---------------------------------------------------------------------------
# preflight: fail CLOSED
# ---------------------------------------------------------------------------
def test_docker_available_returns_bool_without_raising():
    # In this nested sandbox the daemon is down; must return False, never raise.
    assert isinstance(sandbox.docker_available(_docker_cfg()), bool)


def test_preflight_fails_closed_when_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "docker_available", lambda cfg: False)
    with pytest.raises(RuntimeError, match="Docker is unavailable"):
        sandbox.DockerSandbox().run_meta_edit(str(tmp_path), "INSTR", _docker_cfg())


def test_preflight_fails_closed_when_image_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "docker_available", lambda cfg: True)
    monkeypatch.setattr(sandbox, "image_exists", lambda cfg: False)
    with pytest.raises(RuntimeError, match="not found"):
        sandbox.DockerSandbox().run_meta_edit(str(tmp_path), "INSTR",
                                              _docker_cfg(sandbox_autobuild=False))


# ---------------------------------------------------------------------------
# full DockerSandbox.run_meta_edit with a FAKE docker (no daemon)
# ---------------------------------------------------------------------------
def _read_dir(base):
    out = {}
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            p = os.path.join(root, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, base)] = f.read()
    return out


def _make_fake_docker(state):
    """Simulate create -> cp IN -> start(edit) -> cp OUT -> rm against an in-memory
    container workspace, so the whole orchestration runs without a daemon."""
    def fake_run(cmd, timeout=None, check=False):
        sub = cmd[1]
        if sub == "cp":
            src, dst = cmd[2], cmd[3]
            if ":" in dst:                      # cp IN: host dir -> container
                base = src[:-2] if src.endswith(os.sep + ".") or src.endswith("/.") else src
                state["ws"] = _read_dir(base)
            else:                               # cp OUT: container -> host dir
                for rel, data in state["ws"].items():
                    p = os.path.join(dst, rel)
                    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                    with open(p, "wb") as f:
                        f.write(data)
        elif sub == "start":                    # the agent "edits" solver.py
            state["ws"]["solver.py"] = state["ws"].get("solver.py", b"") + b"\n# edited in sandbox\n"
            return SimpleNamespace(returncode=0, stderr="", stdout=(
                '{"is_error": false, "result": "done", "num_turns": 3, '
                '"total_cost_usd": 0.42}'))
        # create / rm / anything else
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return fake_run


def test_docker_run_meta_edit_end_to_end(monkeypatch, tmp_path):
    child = tmp_path / "gen_0001"
    child.mkdir()
    (child / "solver.py").write_text("class Solver: pass\n")
    (child / "meta_strategy.md").write_text("playbook\n")
    (child / "EVAL_REPORT.md").write_text("report\n")

    monkeypatch.setattr(sandbox, "docker_available", lambda cfg: True)
    monkeypatch.setattr(sandbox, "image_exists", lambda cfg: True)
    monkeypatch.setattr(sandbox, "_run", _make_fake_docker({"ws": {}}))

    llm.reset_accounting()
    res = sandbox.DockerSandbox().run_meta_edit(str(child), "INSTR", _docker_cfg())

    # result parsed from the container's stdout json
    assert res["is_error"] is False
    assert res["num_turns"] == 3 and res["cost_usd"] == 0.42
    # the in-container edit was extracted back into the host node dir
    assert (child / "solver.py").read_text().endswith("# edited in sandbox\n")
    # accounting recorded exactly one meta call
    acct = llm.accounting()
    assert acct["calls"] == 1 and acct["by_role"].get("meta") == 1
