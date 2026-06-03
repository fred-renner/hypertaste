#!/usr/bin/env bash
# Build the agent-plane image used by DockerSandbox (hta/sandbox.py). Build context is
# docker/ only, so no project code, .env, or world source is sent to the daemon.
set -euo pipefail

IMAGE="${HTA_SANDBOX_IMAGE:-hypertaste-agent:latest}"
DOCKER_BIN="${HTA_DOCKER_BIN:-docker}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

echo "Building agent-plane image: ${IMAGE}"
"${DOCKER_BIN}" build -t "${IMAGE}" -f "${HERE}/docker/Dockerfile.agent" "${HERE}/docker"

echo
echo "Done. Use it with:"
echo "  export CLAUDE_CODE_OAUTH_TOKEN=...   # or ANTHROPIC_API_KEY=..."
echo "  python run_iteration.py --backend real --sandbox docker [other flags]"
