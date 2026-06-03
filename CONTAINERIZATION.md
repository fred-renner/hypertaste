# Containerization — production-grade airgap for the meta agent (TODO 3)

This note resolves TODO 3 from `HANDOFF.md`: isolate the self-modifying **meta agent**
so a runaway/self-modifying agent cannot touch the host, secrets, or the world source.
It records the threat model, the design, the open questions and how each was resolved,
and exactly which files changed.

For the overall architecture (the three planes, the airgap, the `claude -p` call map)
see `README.md`; for how HyperAgents does the docker-per-generation sandbox we mirror,
see `REFERENCE.md`.

## Why the meta agent is the thing to contain

Of the three `claude -p` call sites, only the **meta agent** is both *self-modifying*
and granted *file-editing tools*:

| call site | tools | risk |
|---|---|---|
| task agent (Haiku, `complete`/`episode`) | none / `mcp__probe__*` only | low — no FS/Bash; the probe MCP tool is the only channel, and it never returns the rule |
| world-smith (Opus, `complete`) | none (`--max-turns 1`) | low — pure text generation, AST-validated before compile |
| **meta agent (Opus, `agentic`)** | **Edit / Read / Write** | **high — edits code, runs every iteration, evolves its own playbook** |

Today the meta agent is airgapped only by **denying Bash** (`cfg.meta_allowed_tools =
("Edit","Read","Write")`). That shrinks the blast radius but is **not a hard
boundary**: the `Read` tool can read absolute host paths, so `hta/world/*` (the hidden
rule + scorer) and a host `.env` are one `Read("/abs/path")` away. Denying Bash is the
lighter mitigation the README always called out as "for production, run the agent plane
in a container."

## Threat model

- **Adversary:** the *model* driving the meta agent (not the `claude` binary, which we
  trust). It may, by accident or via a poisoned eval report, try to read host secrets
  or the world source, write outside its workspace, or exfiltrate data.
- **Assets to protect:** (1) the hidden rule + scorer (`hta/world/*`) — leaking it
  breaks scientific validity, not just security; (2) host secrets (`.env`, tokens);
  (3) the host filesystem generally.
- **Out of scope (documented future work):** a malicious `claude` binary; side
  channels through the model weights; the task-episode session (see below).

## Design: claude runs *inside* an ephemeral container

`hta/sandbox.py` adds a `Sandbox` strategy chosen by `cfg.sandbox`:

- **`none` → `DirectSandbox`** (default): the pre-TODO-3 path — `claude -p` agentic
  in-process, Bash denied. Mock/tests are byte-for-byte unaffected.
- **`docker` → `DockerSandbox`**: a hard boundary. Per child:

  ```
  docker create  (isolated, non-root, resource-limited, NO host mounts)
  docker cp  child_workspace/.  ->  container:/workspace      # copy IN
  docker start --attach                                       # claude edits in-container
  docker cp  container:/workspace/.  ->  tmp                  # copy OUT (extract)
  apply diff  tmp -> child node dir                           # only changed files
  docker rm -f                                                # reset
  ```

  The container holds **no host filesystem, no `.env`, no `hta/world/*`** — the hidden
  rule is never in the image or the container. The workspace (`solver.py`,
  `meta_strategy.md`, the sanitized `EVAL_REPORT.md`) is copied in *after* create and
  the edited result copied back out, so the container's only view of host data is the
  child program itself. Image: `docker/Dockerfile.agent` (Node + Claude Code CLI, a
  non-root `agent` user, `WORKDIR /workspace`; **no project code baked in**).

### Isolation applied (`DockerSandbox._create_cmd`)

`--network <policy>` · `--memory` · `--cpus` · `--pids-limit` · `--cap-drop ALL` ·
`--security-opt no-new-privileges` · non-root user (from the image) · **no `-v` host
bind mount of any kind**.

## Open questions (from HANDOFF.md) → resolutions

1. **"Run claude inside the container, or mount the workspace and run claude on the
   host?"** → **Inside.** Containment of `Edit/Read/Write` is determined by *which
   filesystem the claude process sees*. If claude runs on the host (even with `cwd` set
   to the workspace), its `Read` tool can still open `/abs/host/path` — no containment.
   Running claude inside means the host FS, `.env`, and `hta/world/*` simply do not
   exist in its namespace. The cost is that the API call now egresses from inside the
   container (see #3).

2. **Credentials without weakening the airgap.** Subscription/API auth is forwarded as
   **environment variables** (`cfg.sandbox_auth_env`: `CLAUDE_CODE_OAUTH_TOKEN`,
   `ANTHROPIC_API_KEY`), *never* as a mounted file, and only for vars actually present.
   Key insight: **with Bash denied, the model has no tool to read its own process
   environment** — `Read` reads files, not `env` — so it cannot exfiltrate the token,
   while a mounted credential *file* would be `Read`-able. An opt-in
   `sandbox_mount_claude_config` (read-only mount of `~/.claude`) exists for
   subscription auth stored on disk, but it is **off by default** and weaker, precisely
   because that file is then `Read`-able.

3. **Network / egress.** `cfg.sandbox_network` (default `bridge`) is configurable.
   Because claude runs inside (see #1) it needs egress to the Anthropic API.
   **Production hardening:** restrict egress to `api.anthropic.com` via an egress proxy
   or a firewalled Docker network (set `sandbox_network` to that network). `none` works
   only if you front it with a same-host LLM proxy. We do not ship a proxy; we make the
   knob explicit and document the recommended posture.

4. **Resource limits.** `--memory` (2g), `--cpus` (2), `--pids-limit` (256), all
   configurable, plus `--cap-drop ALL` and `no-new-privileges`. Ephemeral per-child
   containers (`create … rm -f`) cap runaway accumulation.

5. **Sandbox the single-session *task* episode too?** Different shape, deferred. The
   task session already gets **no FS/Bash tools** — its only channel is the `probe` MCP
   tool — so its containment story is about (a) not letting the Haiku session escape and
   (b) keeping the **probe server (which owns the hidden rule via `HTA_RULE_SRC`) OUT of
   the agent's container**. That means the probe server stays host-side while the
   session runs containerized, talking over the stdio-MCP boundary across the container
   wall — solvable but more plumbing than the meta agent, and lower risk. Tracked as
   follow-up; the meta agent is the stated "done when."

## Fail-closed

A security boundary must not silently downgrade. `--sandbox docker` **raises** if the
daemon is unreachable or the image is missing (with a message pointing at
`scripts/build_agent_image.sh` / `HTA_SANDBOX_AUTOBUILD=1`) rather than falling back to
the soft airgap. `--sandbox none` is the explicit way to accept the lighter mitigation.

## Usage

```bash
scripts/build_agent_image.sh                       # build hypertaste-agent:latest once
export CLAUDE_CODE_OAUTH_TOKEN=...                 # or ANTHROPIC_API_KEY=...
python run_iteration.py --backend real --sandbox docker \
  --episode-mode single_session --max-probes 8 --n-train 2 --n-transfer 2
```

Knobs (all have `HTA_SANDBOX_*` env equivalents — see `hta/config.py`): `sandbox`,
`sandbox_image`, `sandbox_network`, `sandbox_memory`, `sandbox_cpus`, `sandbox_pids`,
`sandbox_autobuild`, `sandbox_docker_bin`, `sandbox_auth_env`,
`sandbox_mount_claude_config`, `sandbox_claude_config_dir`.

## What changed

| file | change |
|---|---|
| `hta/sandbox.py` | **new** — `DirectSandbox`/`DockerSandbox`, factory, docker preflight, `apply_workspace_changes` (extract), `_run` seam |
| `hta/llm.py` | factored `agentic_argv()` + `agentic_result_from_stdout()` so on-host and in-container share the airgap flags; `agentic()` now uses them |
| `hta/config.py` | `sandbox*` knobs + `HTA_SANDBOX_*` env overrides |
| `hta/meta_agent.py` | routes the agentic edit through `sandbox.get_sandbox(cfg)` |
| `docker/Dockerfile.agent`, `docker/README.md` | agent-plane image (no project code/world/secrets) |
| `scripts/build_agent_image.sh` | one-shot image build (context = `docker/` only) |
| `run_iteration.py`, `run_loop.py` | `--sandbox none|docker` flag + banner |
| `tests/test_sandbox.py` | **new** — 10 daemon-free tests: routing, diff/apply, isolation flags, env-only creds, fail-closed, full faked `create→cp→start→cp→rm` |

## Done-when (TODO 3) — status

- ✅ **No readable path to host secrets or the world:** claude runs in a container with
  no host bind mounts; the world source and `.env` are absent; creds are env-only and
  unreadable by a no-Bash agent.
- ✅ **edit → diff → reset cycle works:** `create → cp in → start → cp out → apply diff
  → rm`, verified end-to-end against a faked docker (no daemon) in `test_sandbox.py`.
- ✅ **existing tests still pass:** 6/6 `test_pipeline.py` unchanged + 10 new sandbox
  tests = 16/16; the mock path never touches the sandbox.

**Not yet validated live:** an actual `docker build` + a real containerized `claude -p`
run (this dev environment has the Docker CLi but no running daemon, and a live run costs
Opus tokens). Everything except the literal `docker` daemon calls is covered by tests;
the daemon calls go through the single `_run` seam. First live run is the natural next
step (build the image, set `CLAUDE_CODE_OAUTH_TOKEN`, `--sandbox docker`).
