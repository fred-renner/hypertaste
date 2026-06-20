"""The DiscoveryWorld arena -- the borrowed world the bet is run against.

BET.md settled the arena: DiscoveryWorld (Ai2, 2024), an interactive text-based scientific-
discovery simulator. The whole program reduces to a *hand-run of LOOP 1* against this fixed world
-- toggle the allocator playbook on vs off and measure the lift. There is no world-smith here
(LOOP 2 is retired for this chapter); the curriculum is DiscoveryWorld's own parametric variations
(a different data/layout/solution per random seed), so the held-out split is built in.

The pieces (mirroring the quarantined trail's airgapped body, hta/_trail/):
  - arena.py   -- the headless adapter over DiscoveryWorldAPI: load a scenario variation, hand the
                  player a *text* observation (no vision), apply one action + tick, and -- harness
                  side only -- read the mechanical scorecard. discoveryworld is an OPTIONAL heavy
                  dependency; it is imported lazily so the stdlib-only suite is unaffected.
  - server.py  -- the confined stdio-MCP tool surface (the airgap): observe / act / actions / notes.
                  The scorecard never crosses it -- it is written to the harness dropbox only.
  - play.py    -- run one episode (a single Haiku claude -p session driving the arena via the MCP
                  airgap, playbook as the system prompt) and read back the scorecard.
  - bench.py   -- the two-arm race: N variations x {allocator, baseline}, aggregate the lift.
  - playbooks/ -- the toggled genome: allocator.md (toggle-on) vs baseline.md (toggle-off).

THE INTEGRITY FLOOR, lifted onto DiscoveryWorld:
  1. Objective, agent-inaccessible scoring -- the score is DiscoveryWorld's own deterministic
     scorecard (`getTaskScorecard`), never an LLM judge. The player's tool surface never exposes it.
  2. Safe-eval -- the evolved unit is the playbook (English, read as the player's system prompt),
     never imported or executed.
"""
