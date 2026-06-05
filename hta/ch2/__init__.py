"""Chapter 2 (the investigation-map) — the thin de-risking slice.

A hand-built tiny grammar-map + DP oracle + a vanilla-vs-taste Haiku measurement,
built to answer the two load-bearing bets (WORLD_DESIGN.md -> "First slice") BEFORE a
cent is spent on the loop:

  bet 1 (realizable gap): does a taste-prompt Haiku beat vanilla Haiku and approach the
         model-free oracle? (gap must be realizable by the student, not merely present.)
  bet 2 (ramp not cliff): is coverage ~linear in the fraction of the grammar inferred?

This package is isolated from the running Chapter-1 code (hta/world/*) so the repo keeps
running Chapter 1 while we measure Chapter 2. Nothing here imports hta.world.
"""
