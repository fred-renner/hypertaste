"""Run one play -- task agent + playbook + confined server -> a recorded result.

Builds the world harness-side (hta.world.spec.build), starts the confined tool server
(server.py), runs the task agent in a single session with the playbook as its system prompt
(via hta.llm.episode), and returns the play result: the conduct (probes, workers, scratchpad,
submission) plus the world's hidden answer for harness-side scoring and the run log.

The result is graded *after* this returns (by hta.lab.scoring.score_run, harness-side) and
sanitized for the meta-agent (by hta.dgmh.report.build_report). This module never grades and
never hands the hidden answer to the player.

Stub: lands when LOOP 1 is wired (reference: `run_episode` in hta/_trail/loop.py). Budget the
play by probes/cost, with generous turn headroom (Gotchas: "probes, not turns, bind").
"""

from __future__ import annotations

from hta.config import Config


def run_play(playbook: str, spec: dict, *, seed: int, cfg: Config) -> object:
    """Run one play and return its full result (conduct + hidden answer). Does not grade."""
    raise NotImplementedError("the play runner lands when LOOP 1 is wired")
