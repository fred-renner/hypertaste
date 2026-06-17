"""The run log -- the quarantined record of plays, hidden answers and all.

Every play is recorded here in full (probes, workers, scratchpad, submission, AND the world's
hidden answer) so a score can be replayed and audited. That makes this the one radioactive
store in the system.

INVARIANT (the quarantine): the run log is never on an agent surface and never a workspace
source for the meta-agent's sandbox. The player sees only its tools (hta/dgmh/play/server.py);
the meta-agent sees only the *sanitized* report (hta/dgmh/report.py) built from the public
face. Nothing that feeds a model prompt may read from here. Keep it out of `hta/archive/`
(the clean stepping-stones) for exactly this reason.

Stub: the writer/reader land when LOOP 1 is wired (the persistence logic in
hta/_trail/loop.py is the reference). Writes under `Config.out_dir`.
"""

from __future__ import annotations


def record(play: object) -> str:
    """Persist one full play (with its hidden answer) and return its path. Radioactive store."""
    raise NotImplementedError("persistence lands when LOOP 1 is wired")


def load(path: str) -> object:
    """Read back a recorded play for replay/audit. Harness-only -- never an agent surface."""
    raise NotImplementedError("persistence lands when LOOP 1 is wired")
