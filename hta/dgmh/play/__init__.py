"""One play -- a single attempt at a world, and the airgap on the play side.

A play runs the task agent (guided by its playbook) against one built world through a confined
set of tools, and records what it did. The pieces:
  - state.py  -- the per-play world-state machine: holds the built world + hidden answer +
                 budget + probe log + scratchpad; the seven primitives as plain methods.
  - server.py -- the confined stdio-MCP tool surface: the ONLY way the player touches the world.
  - run.py    -- run one play: spin up the task agent + playbook + server, collect the result.

THE AIRGAP, STATED PRECISELY (it is tool confinement, not an import wall):
The play *harness* (state.py) legitimately holds the built world -- it must, to answer a probe.
The *player* (the model session) reaches the world only through server.py's tools and has no
filesystem/Bash tools. So the lintable rules are:
  1. nothing reachable from the player's tool surface exposes the hidden answer, and
  2. `hta/dgmh/play/` imports the `World` *shape* from hta.lab.scoring (to type the opaque
     handle) but never the grader functions (oracle / floor / score_run / grade_world) --
     grading happens after the play, harness-side, out of the player's reach. (Lintable: no
     oracle|floor|score_run|grade_world reference under hta/dgmh/play/.)
The world is built by the harness (via hta.world.spec.build) and held as an opaque handle typed
by hta.lab.scoring.World. See DESIGN.md (the integrity floor) and CLAUDE.md (the airgap).
"""
