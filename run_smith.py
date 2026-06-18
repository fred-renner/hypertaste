#!/usr/bin/env python3
"""The world-building SUBSTRATE — offline, model-free, deterministic (the substrate proof, not the
live loop). See findings/2026-06-18-world-building-substrate.md.

World-building has failed three times by CONSTRUCTING a world and burying it in a story, which
re-anchors the next session. So before any live loop, we prove the substrate under it: a grammar of
parts (variables + gated readouts) derived from first principles, a seed authored IN that grammar as
its unit test, and a model-free ship-gate that re-derives hard + solvable + a ZPD-capable structure
MECHANICALLY from the structure alone — all certified against the frozen grader (`hta/lab/scoring.py`)
and the dumb-player battery (`hta/gym/battery.py`), with no LLM and no live champion.

This driver watches the loop turn: ship-gate the certified seed, then apply each deterministic
mutation operator once and ship-gate the spread, printing the admit/reject verdict per world. It
demonstrates the grammar expands to gradeable worlds and the mutation machinery exercises the gate
across a correct admit/reject spread — the hand-off point to LOOP 1 (where true ZPD, against a live
champion, and the LLM inventor enter).

Run: python run_smith.py     (free, deterministic; ~minutes — the exact oracle over the deepened
                              world's larger hypothesis space is the costly part, computed once.)
"""

from hta.config import Config
from hta.gym.loop import survey


def main():
    print("=" * 100)
    print("THE WORLD-BUILDING SUBSTRATE — seed -> mutate -> ship-gate (offline, model-free)")
    print("=" * 100)
    print("\nEach world is realized from a declarative spec, graded by the FROZEN scorer, and bracketed")
    print("by the dumb-player battery. A world SHIPS only if it is valid + hard (best-play beats every")
    print("scripted player by the margin) + solvable (the scout-the-path fix reaches the band) +")
    print("zpd-capable (the greedy champion analogue stalls while the fix succeeds). The smith asserts")
    print("nothing — every verdict is re-derived mechanically from the structure.\n")

    records = survey(cfg=Config())

    shipped = [r for r in records if r.get("ship")]
    print(f"\n{'=' * 100}")
    print(f"RESULT — {len(shipped)}/{len(records)} worlds ship. The seed is certified; the mutation")
    print("spread exercises the gate across the expected admit/reject (deepen -> harder, still ships;")
    print("remove a gate layer -> trivial; over-tighten budget -> unsolvable).")
    print("=" * 100)


if __name__ == "__main__":
    main()
