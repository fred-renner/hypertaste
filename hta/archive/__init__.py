"""The shared stepping-stone archive -- the open-ended store both loops draw on.

LOOP 1 and LOOP 2 are the same move: keep a library of past attempts, pick a promising one,
mutate it, score it, admit it. LOOP 1 does this to *playbooks*, LOOP 2 to *world specs*.
The store + parent-selection (quality x novelty) + the program-length prior are world- and
artifact-agnostic, so they belong here, instantiated twice over the two artifact types --
not reimplemented per loop.

Stub / intent home: the working implementation currently lives at `hta/dgmh/archive.py`
(it backs the quarantined `_trail/`). It moves here once `_trail/` retires, and both loops
import it from this package. Until then this docstring marks the destination.

NOT this package: the run log (the recorded plays *with* hidden answers). That is radioactive
-- it must never share a tree or a class with the agent-facing stepping-stones. It lives in
`hta/run_logs.py`. See DESIGN.md (the archive holds "all past worlds, episodes, plays,
lineage" -- but the hidden-state record is quarantined separately).
"""
