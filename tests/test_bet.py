"""bet/ seam tests -- offline, deterministic, no model cost.

These exercise the confined action interface end-to-end through the mock backend:
the world server, the socket protocol, the move budget, and the out-of-band
score. They require the borrowed world (run bet/setup_world.sh); if it isn't
present the whole module skips rather than failing.

The load-bearing claims:
  * The agent's confined client cannot read the score (the integrity floor:
    scoring is agent-inaccessible).
  * The move budget binds: an episode never spends more than max_steps.
  * A mock episode yields the objective DiscoveryWorld scorecard out-of-band.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bet"))

# Skip the whole module unless the borrowed world is available.
import dw_world  # noqa: E402
try:
    dw_world._locate_discoveryworld()
    import discoveryworld.DiscoveryWorldAPI  # noqa: F401
    _HAVE_WORLD = True
except Exception:
    _HAVE_WORLD = False

pytestmark = pytest.mark.skipif(not _HAVE_WORLD,
                                reason="DiscoveryWorld not installed (run bet/setup_world.sh)")

SCENARIO, DIFFICULTY = "Proteomics", "Normal"


def test_score_is_not_agent_reachable():
    """The privileged `scorecard` command is not in the client's command set."""
    import server
    assert "scorecard" not in server._AGENT_CMDS
    assert {"observe", "act", "actions", "locations", "status"} <= server._AGENT_CMDS


def test_mock_episode_scores_out_of_band_and_respects_budget():
    import episode
    budget = 4
    r = episode.run_episode("off", SCENARIO, DIFFICULTY, seed=0,
                            backend="mock", max_steps=budget, thread_id=101)
    sc = r["scorecard"]
    # The objective scorecard came back, with the metrics the bet measures.
    for key in ("completed_successfully", "process_score", "steps_used"):
        assert key in sc
    assert 0.0 <= sc["process_score"] <= 1.0
    # The budget binds: never more moves than allowed.
    assert sc["steps_used"] <= budget


def test_curated_view_is_lean_and_hides_the_score():
    """A direct world view is curated (no raw nearbyObjects flood) and carries no
    score field."""
    w = dw_world.World(SCENARIO, DIFFICULTY, seed=0, max_steps=5, thread_id=102)
    view = w.agent_view()
    assert "task" in view and view["task"]
    assert "budget_remaining" in view
    # No score leaks into the agent's view.
    for forbidden in ("process_score", "score", "completed_successfully", "scoreCard"):
        assert forbidden not in view
    # The scorecard, read out-of-band, does carry it.
    assert "process_score" in w.scorecard()
