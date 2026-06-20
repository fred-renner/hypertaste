"""The world server: holds one DiscoveryWorld episode behind a Unix socket.

Started by the harness (episode.py) with a scenario/difficulty/seed/budget. The
agent never imports this or the world -- it only sends the whitelisted read/act
commands through the client (dw.py). The `scorecard` command is privileged: the
client never sends it, so the agent can't read its own score (the integrity
floor -- the score is agent-inaccessible).

Single-threaded, one request per connection. Run:
    python -m bet.server --socket /tmp/x.sock --scenario Proteomics \
        --difficulty Normal --seed 0 --max-steps 40 --thread-id 1
"""

import argparse
import json
import os
import socket
import sys

# Allow both `python -m bet.server` and `python bet/server.py`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dw_world import World  # noqa: E402

# Commands the confined client is allowed to surface. `scorecard` is omitted on
# purpose: it is privileged and only the trusted harness sends it.
_AGENT_CMDS = {"observe", "actions", "locations", "status", "act"}


def _handle(world: World, req: dict) -> dict:
    cmd = req.get("cmd")
    if cmd == "observe":
        return {"ok": True, "obs": world.agent_view()}
    if cmd == "actions":
        return {"ok": True, "actions": world.actions()}
    if cmd == "locations":
        return {"ok": True, "locations": world.locations()}
    if cmd == "status":
        return {"ok": True, "budget_remaining": world.budget_remaining,
                "steps_used": world.steps_used}
    if cmd == "act":
        if world.budget_remaining <= 0:
            return {"ok": True, "episode_over": True,
                    "result": "Budget exhausted. The episode is over; no more "
                              "actions can be taken."}
        action = req.get("action") or {}
        try:
            out = world.act(action)
        except Exception as e:  # a malformed action must not kill the server
            return {"ok": False, "error": f"action failed: {e}"}
        out.update({"ok": True, "obs": world.agent_view()})
        return out
    if cmd == "scorecard":  # privileged -- harness only
        return {"ok": True, "scorecard": world.scorecard()}
    if cmd == "ping":
        return {"ok": True, "pong": True}
    return {"ok": False, "error": f"unknown cmd: {cmd!r}"}


def serve(sock_path: str, world: World) -> None:
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(8)
    print(f"[server] ready on {sock_path}", file=sys.stderr, flush=True)
    try:
        while True:
            conn, _ = srv.accept()
            try:
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                if not buf:
                    continue
                req = json.loads(buf.decode("utf-8").strip())
                resp = _handle(world, req)
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                if req.get("cmd") == "shutdown":
                    break
            except Exception as e:
                try:
                    conn.sendall((json.dumps({"ok": False, "error": str(e)}) + "\n").encode())
                except Exception:
                    pass
            finally:
                conn.close()
    finally:
        srv.close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--socket", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--difficulty", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--thread-id", type=int, default=1)
    args = ap.parse_args()
    world = World(args.scenario, args.difficulty, args.seed,
                  args.max_steps, args.thread_id)
    print(f"[server] loaded {args.scenario}/{args.difficulty}/seed{args.seed} "
          f"budget={args.max_steps}", file=sys.stderr, flush=True)
    serve(args.socket, world)


if __name__ == "__main__":
    main()
