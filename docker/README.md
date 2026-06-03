# Agent-plane container

`Dockerfile.agent` builds the minimal image that runs the self-modifying **meta
agent** in isolation (TODO 3 / production-grade airgap). Rationale, threat model, and
the resolved open questions are in [`../CONTAINERIZATION.md`](../CONTAINERIZATION.md).

## Build

```bash
scripts/build_agent_image.sh           # -> hypertaste-agent:latest
# or:
docker build -t hypertaste-agent:latest -f docker/Dockerfile.agent docker/
```

The build context is just this `docker/` directory, so **no project code, `.env`, or
world source is ever sent to the daemon or baked into the image**. The child workspace
is copied into the container at run time by `hta/sandbox.py` and the edited result is
copied back out; the container is then destroyed.

## Run (via the harness)

```bash
# subscription auth as an env token (preferred -- a no-Bash agent can't read its env):
export CLAUDE_CODE_OAUTH_TOKEN=...        # or ANTHROPIC_API_KEY=...
python run_iteration.py --backend real --sandbox docker \
  --episode-mode single_session --max-probes 8 --n-train 2 --n-transfer 2
```

`--sandbox docker` fails **closed**: if the daemon is down or the image is missing it
raises rather than silently falling back to the soft (Bash-denied) airgap.
