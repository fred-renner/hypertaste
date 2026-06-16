#!/usr/bin/env bash
# Build the agent-plane image used by DockerSandbox (hta/dgmh/sandbox.py). Build context is
# docker/ only, so no project code, .env, or world source is sent to the daemon.
set -euo pipefail

IMAGE="${HTA_SANDBOX_IMAGE:-hypertaste-agent:latest}"
DOCKER_BIN="${HTA_DOCKER_BIN:-docker}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

echo "Building agent-plane image: ${IMAGE}"
"${DOCKER_BIN}" build -t "${IMAGE}" -f "${HERE}/docker/Dockerfile.agent" "${HERE}/docker"

echo
echo "Done. Use it with (auth defaults to the host's ~/.claude, mounted read-only):"
echo "  python run_iteration.py --backend real --sandbox docker [other flags]"
echo
echo "To auth with an env token instead, set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY."
