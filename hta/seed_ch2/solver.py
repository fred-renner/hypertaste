"""Chapter-2 seed task-agent program (the unit that evolves) -- a NEUTRAL investigator.

It reconstructs a hidden register world: M cells, each a FIXED, PUBLIC function of R hidden
registers, recovered under a scarce probe budget (`WORLD_DESIGN.md` -> the register world,
`trap-tetra`). It interacts with the world ONLY through `channel` (probe a cell -> its color;
the cell formulas are public via `channel.world_map()`) and reasons ONLY through `llm` (the
task model, Haiku, a stateless completion oracle).

Like the Chapter-1 seed it ships with **no pre-loaded research taste**: the prompts below
state the task and ask for a next cell to probe / a full reconstruction, and say nothing
about *how* to investigate well -- no "probe the linked block", no "solve the registers
jointly", no "spend where uncertainty is highest". Growing taste -- how to allocate the
budget across direct vs. buried blocks, when to gather an equation rather than a value, how
to externalize what's known, when to compute the rest deterministically instead of guessing --
is the meta agent's job, **discovered from the trajectory evidence**, never shipped here. A
pre-loaded recipe is the null hypothesis (taste frozen at the designer's articulable ceiling);
the seed must be a blank slate so any taste the system shows was grown, not installed.

Contract (the meta agent must preserve this):
    class Solver:
        def run(self, channel, llm) -> list[int]   # a reconstruction: one color per cell

`channel`: probe(index)->int|None, remaining()->int, world_map()->{M,K,R,budget,cells:[...]}.
`llm`: llm(prompt, role) -> str (constrained completion on the task model).
It must not import any world/engine internals; interact only via channel and llm. A real meta
agent may replace this whole file with something better, as long as the contract holds.

`_MOCK_VARIANT` is **not** research content -- it is a hook the deterministic mock backend
reads to make an offline behavior change observable after a meta edit (the mock llm returns no
usable plan, so the seed falls back to a deterministic fill; the flip changes that fill). The
real task model never sees it and the real meta agent may delete it.
"""

import json
import re

_MOCK_VARIANT = "seed"   # mock-only plumbing fixture; the mock meta edit flips it to "edited".


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_]*|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


class Solver:
    def run(self, channel, llm):
        info = channel.world_map()
        M, K = info["M"], info["K"]
        obs = {}  # index -> observed color
        while channel.remaining() > 0:
            idx = self._next_probe(info, obs, channel.remaining(), llm)
            if idx is None or idx in obs:
                idx = self._fallback_probe(M, obs)
            if idx is None:
                break
            val = channel.probe(idx)
            if val is not None:
                obs[idx] = val
        return self._reconstruct(info, obs, llm)

    # ---- probing ----
    def _next_probe(self, info, obs, remaining, llm):
        prompt = (
            f"You are reconstructing {info['M']} hidden cells (each an integer color in "
            f"0..{info['K'] - 1}). Every cell is a fixed, known function of {info['R']} hidden "
            f"registers r0..r{info['R'] - 1} (unknown integers in 0..{info['K'] - 1}). "
            "The per-cell formulas:\n"
            f"{self._fmt_formulas(info)}\n\n"
            f"Cells you have probed so far:\n{self._fmt_obs(obs)}\n"
            f"Probes remaining: {remaining}.\n\n"
            "Choose the next cell to probe.\n"
            'Respond ONLY with JSON: {"probe": <cell index>}'
        )
        idx = (_extract_json(llm(prompt, role="ch2_probe")) or {}).get("probe")
        return idx if isinstance(idx, int) and not isinstance(idx, bool) else None

    def _fallback_probe(self, M, obs):
        for i in range(M):
            if i not in obs:
                return i
        return None

    # ---- reconstructing ----
    def _reconstruct(self, info, obs, llm):
        M, K = info["M"], info["K"]
        prompt = (
            f"You have finished probing a world of {M} hidden cells (colors 0..{K - 1}), each a "
            f"known function of {info['R']} hidden registers (values 0..{K - 1}). The per-cell "
            "formulas:\n"
            f"{self._fmt_formulas(info)}\n\n"
            f"The cells you probed and observed:\n{self._fmt_obs(obs)}\n\n"
            f"Give the color of EVERY cell, indices 0..{M - 1}, in order.\n"
            'Respond ONLY with JSON: {"cells": [c0, c1, ..., cN]}'
        )
        cells = (_extract_json(llm(prompt, role="ch2_recon")) or {}).get("cells")
        if isinstance(cells, list) and len(cells) == M and all(
                isinstance(c, int) and not isinstance(c, bool) for c in cells):
            return [c % K for c in cells]
        return self._fallback_recon(M, K, obs)

    def _fallback_recon(self, M, K, obs):
        # No usable plan from the llm (e.g. the mock backend): place what was observed and fill
        # the rest with a default. _MOCK_VARIANT only changes that default so the offline loop
        # is observable; it encodes no inference (the real path never reaches here).
        if _MOCK_VARIANT == "edited" and obs:
            fill = max(set(obs.values()), key=lambda v: list(obs.values()).count(v))
        else:
            fill = 0
        return [obs.get(i, fill) for i in range(M)]

    # ---- formatting ----
    @staticmethod
    def _fmt_formulas(info):
        return "\n".join(f"  cell {c['index']}: {c['formula']}" for c in info["cells"])

    @staticmethod
    def _fmt_obs(obs):
        if not obs:
            return "  (none yet)"
        return "\n".join(f"  cell {i} -> {obs[i]}" for i in sorted(obs))
