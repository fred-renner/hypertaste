"""The cheap trajectory visualization (PLAN.md -> design lock 9: "a run you can't inspect didn't
happen"). A pure renderer: a finished episode result (the probe log, spawns, scratchpad,
submission) + its spec -> compact markdown — the step-by-step probe trace in public cell terms,
the discovered map sketch (what the link/key/backbone reads pinned of the hidden shape), and the
outcome line. No LLM, no tokens; it reads only what the player itself observed, so it can leak
nothing the player did not earn."""

from typing import List, Optional

from . import anchor


def render(spec, result: dict, score: Optional[dict] = None) -> str:
    cells = spec.cells()
    describe = getattr(spec, "describe_cell", lambda c: str(c))
    lines: List[str] = [f"# Trajectory — {spec.name}"]

    log = result.get("log", [])
    lines.append(f"\n## Probes ({len(log)}; cost used {result.get('used', '?')}/{spec.budget})")
    if not log:
        lines.append("(none)")
    for n, e in enumerate(log, 1):
        via = "" if e.get("via") == "self" else f"  [{e.get('via')}]"
        lines.append(f"{n:>2}. {describe(cells[e['col']]):<18} -> {e['value']}"
                     f"  (col {e['col']}, cost {e.get('cost', '?')}){via}")

    sketch = _sketch(spec, {e["col"]: e["value"] for e in log})
    if sketch:
        lines.append("\n## Discovered map")
        lines.extend(sketch)

    for j, sp in enumerate(result.get("spawns", [])):
        lines.append(f"\n## Worker {j}: used {sp.get('used')}, {sp.get('n_obs')} cells; "
                     f"task: {sp.get('task', '')!r}")

    mem = (result.get("mem") or "").strip()
    if mem:
        lines.append("\n## Scratchpad\n" + mem)

    sub = result.get("submitted") or {}
    lines.append(f"\n## Submission: {len(sub)} cells")
    if score:
        lines.append(f"score: raw {score.get('raw')} of band "
                     f"{score.get('floor')}->{score.get('oracle', score.get('ceiling'))} "
                     f"(norm {score.get('norm')})")
    return "\n".join(lines)


def _sketch(spec, obs: dict) -> List[str]:
    """The hidden-map sketch: per group, the realized path as far as the link reads pinned it,
    plus key/backbone status. Trail-shaped specs (no `groups`) get no sketch — the probe trace
    already is their story."""
    if not hasattr(spec, "groups"):
        return []
    cells = spec.cells()
    link_col, key_col, backbone_col = {}, {}, None
    for col, c in enumerate(cells):
        if c[0] == "link":
            link_col[(c[1], c[2], c[3])] = col
        elif c[0] == "key":
            key_col[c[1]] = col
        elif c[0] == "backbone":
            backbone_col = col

    out = []
    for gi, g in enumerate(spec.groups):
        hops, li, idx = ["entry"], 0, 0
        stop = False
        while True:
            if li == len(g.layers):             # walked into the final layer (or layerless)
                stop = True
                break
            v = obs.get(link_col.get((gi, li, idx)))
            if v is None:
                hops.append("?")
                break
            if v == 1:
                stop = True
                break
            li, idx = li + 1, v - 2
            hops.append(f"[{li},{idx}]")
        path = " -> ".join(hops) + (" -| stop" if stop else "")
        k = obs.get(key_col.get(gi))
        key = f"key={k}" if k is not None else "key=?"
        out.append(f"g{gi} ({'coupled' if g.coupled else 'uncoupled'}, "
                   f"region {g.region_len}): {path}; {key}")
    if backbone_col is not None:
        b = obs.get(backbone_col)
        out.append(f"backbone={'?' if b is None else b}")
    return out
