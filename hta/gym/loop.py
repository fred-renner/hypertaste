"""The curriculum -- the LOOP-2 iteration that grows the worlds.

At saturation: the smith proposes a world -> the ship-gate admits or rejects it -> an admitted
world is handed to LOOP 1, the champion is coached on it, and a passing champion graduates and
carries forward. Evolved worlds accumulate in the shared archive as stepping-stones.

Kept distinct from hta/dgmh/loop.py on purpose: this loop's "evaluate" is the model-free,
deterministic ship-gate, where LOOP 1's is live, stochastic play. Only the archive primitive is
shared beneath them.

STATUS: stubbed -- built after LOOP 1 climbs. Reference: `run_curriculum` in
hta/_trail/world_smith.py.
"""
