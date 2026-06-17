"""The ship-gate -- admit a proposed world only if it earns its place.

Realize the smith's spec via the lab, then gate on the lab's grade: hard (wide best/lazy gap,
so skill matters), solvable (the top reachable within budget), and ZPD (just past the current
champion's reach -- coachable in one stage). The grade is re-derived mechanically from the
structure; the smith never asserts it. A world that fails is rejected, not rescued.

STATUS: stubbed -- built after LOOP 1 climbs. Reference: `ship_gate` in
hta/_trail/world_smith.py.
"""
