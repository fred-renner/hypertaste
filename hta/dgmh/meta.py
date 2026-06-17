"""The meta-edit -- grow the player by rewriting its playbook.

Given a parent playbook and a sanitized conduct report (hta/dgmh/report.py), the meta-agent
rewrites the playbook into a child. The playbook is non-executable English: it is read as the
player's system prompt, never imported or run (safe-eval).

The rewrite runs behind the world airgap (hta/dgmh/sandbox.py): the meta-agent edits text in a
workspace and never sees the world source, the grader, or the hidden answer -- only the
report. Direct sandbox denies Bash; Docker runs it in a container with no repo or world source.

Stub: the edit step lands when LOOP 1 is wired (the reference is `meta_edit` in
hta/_trail/loop.py). The expensive call in the system (an Opus edit ~ $1) -- one per iteration.
"""

from __future__ import annotations

from hta.config import Config


def meta_edit(parent_dir: str, child_dir: str, report_md: str, cfg: Config) -> None:
    """Branch the parent playbook into `child_dir` and rewrite it from `report_md`, via sandbox."""
    raise NotImplementedError("the meta-edit lands when LOOP 1 is wired")
