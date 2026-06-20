"""dw -- the only thing the agent can do.

This is the confined action interface (the airgap). The agent drives the world
ONLY through these commands; it never sees the world's code or its score.

Usage:
  python dw.py observe                 # what you see right now
  python dw.py actions                 # the moves you can make
  python dw.py locations               # named places you can teleport to
  python dw.py act '<json>'            # make a move, e.g.
        python dw.py act '{"action":"TELEPORT_TO_LOCATION","arg1":"Instrument Table"}'
        python dw.py act '{"action":"READ","arg1":12345}'
        python dw.py act '{"action":"USE","arg1":12345,"arg2":67890}'
  python dw.py act '{"chosen_dialog_option_int": 2}'   # when in a dialog

Object arguments (arg1/arg2) are the integer UUIDs shown in `observe`.
The socket to the world is read from $BET_SOCKET.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc import call  # noqa: E402


def _sock() -> str:
    p = os.environ.get("BET_SOCKET")
    if not p:
        print("ERROR: BET_SOCKET is not set.", file=sys.stderr)
        sys.exit(2)
    return p


def _fmt_obs(obs: dict) -> str:
    L = []
    L.append(f"STEP {obs.get('step')} | BUDGET {obs.get('budget_remaining')} actions left")
    L.append(f"TASK: {obs.get('task','')}")
    loc = obs.get("location", {})
    L.append(f"LOCATION: ({loc.get('x')},{loc.get('y')}) facing {loc.get('facing')} | "
             f"can move: {', '.join(loc.get('can_move', []) or ['-'])}")
    if obs.get("last_action"):
        L.append(f"LAST RESULT: {obs['last_action']}")
    if obs.get("in_dialog"):
        d = obs.get("dialog", {})
        L.append(f"\nIN DIALOG. NPC says: {d.get('npc_says','')}")
        L.append("Reply by choosing an option number with "
                 "act '{\"chosen_dialog_option_int\": N}':")
        for k, v in (d.get("options") or {}).items():
            L.append(f"  {k}: {v}")
        return "\n".join(L)
    inv = obs.get("inventory") or []
    L.append(f"INVENTORY: {', '.join(inv) if inv else '(empty)'}")
    acc = obs.get("accessible") or []
    L.append("ACCESSIBLE NOW (you can act on these): "
             + (", ".join(acc) if acc else "(nothing in reach -- teleport closer)"))
    nearby = obs.get("nearby") or {}
    if nearby:
        L.append("NEARBY (teleport to a uuid or a named location to get in reach):")
        for direction, items in nearby.items():
            L.append(f"  {direction}: {', '.join(items)}")
    return "\n".join(L)


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__)
        return
    cmd = argv[0]
    sock = _sock()

    if cmd == "observe":
        r = call(sock, {"cmd": "observe"})
        print(_fmt_obs(r["obs"]))
    elif cmd == "actions":
        r = call(sock, {"cmd": "actions"})
        for name, spec in r["actions"].items():
            args = ", ".join(spec.get("args", [])) or "none"
            print(f"{name}  (args: {args})  -- {spec.get('desc','')}")
    elif cmd == "locations":
        r = call(sock, {"cmd": "locations"})
        names = list(r["locations"].keys())
        print("Teleport with act '{\"action\":\"TELEPORT_TO_LOCATION\",\"arg1\":\"<name>\"}':")
        for n in names:
            print(f"  - {n}")
    elif cmd == "act":
        if len(argv) < 2:
            print("ERROR: act needs a JSON action, e.g. "
                  "act '{\"action\":\"READ\",\"arg1\":123}'", file=sys.stderr)
            sys.exit(2)
        try:
            action = json.loads(argv[1])
        except json.JSONDecodeError as e:
            print(f"ERROR: bad JSON action: {e}", file=sys.stderr)
            sys.exit(2)
        r = call(sock, {"cmd": "act", "action": action})
        if r.get("episode_over"):
            print(r.get("result", "Episode over."))
            return
        if not r.get("ok"):
            print(f"ACTION ERROR: {r.get('error')}")
            return
        print(f"RESULT: {r.get('result','')}")
        if r.get("done"):
            print("** TASK COMPLETE **")
        print("\n" + _fmt_obs(r["obs"]))
    else:
        print(f"ERROR: unknown command {cmd!r}. Try: observe | actions | "
              "locations | act | help", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
