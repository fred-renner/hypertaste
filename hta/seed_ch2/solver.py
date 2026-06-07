"""Chapter-2 seed task-agent program (the unit that evolves) -- a NEUTRAL, MINIMAL harness.

The task agent is itself a *harness*: it deploys claude-agent session(s) over an unknown
register world (M cells, each a FIXED, PUBLIC function of R hidden registers, recovered under a
scarce probe budget -- `WORLD_DESIGN.md` -> the register world, `trap-tetra`) and assembles a
reconstruction. It reaches the world ONLY by spawning an agent (`ctx.run_agent`); the cell
formulas are public (`ctx.world_map()`); the register values are the only hidden information.

This seed is the SMALLEST possible harness: it deploys ONE agent with the whole budget, hands it
the public map, and lets it probe and submit. That happens to reproduce the single-session
student the world was calibrated against -- a deliberate, neutral starting point, NOT a claim
that one agent is the right architecture. It ships with **no pre-loaded research taste** and **no
fixed architecture**: how to split the work across agents, decompose by block, externalize what's
known, solve the registers in Python rather than asking a model to eyeball them, decide when to
stop -- all of that is the meta agent's to discover from the trajectory evidence, never shipped
here. A pre-loaded recipe (or a hardcoded architecture) is the null hypothesis; the seed must be
a blank slate so any taste the system shows was grown, not installed.

Contract (the meta agent must preserve this):
    class Solver:
        def run(self, ctx) -> list[int]   # a reconstruction: one color per cell, length M

`ctx` capabilities:
    ctx.world_map()        -> {M, K, R, budget, cells:[{index,coeffs,const,formula}, ...]}
    ctx.remaining()        -> probes left in the GLOBAL budget (shared across all agents)
    ctx.observations()     -> {cell_index: observed_color} accumulated across every agent so far
    ctx.run_agent(prompt, *, max_probes=None, max_turns=None, extra_tools=())
        -> {submission, observations, probes_used, result}
       Deploys one airgapped claude session (tools: probe(index), remaining(), submit_map(values))
       that may probe up to max_probes of the remaining budget and optionally submit a map.

The program imports no world internals; it gets the world only through `ctx`. A real meta agent
may replace this whole file with a better harness, as long as the contract holds.

`_MOCK_VARIANT` is **not** research content -- it is a hook the deterministic mock backend reads
to make an offline behavior change observable after a meta edit (the mock agent never submits, so
the seed assembles from observations; the flip changes the unobserved-cell fill). The real path
takes the agent's own submission and never reaches it; the real meta agent may delete it.
"""

_MOCK_VARIANT = "seed"   # mock-only plumbing fixture; the mock meta edit flips it to "edited".


class Solver:
    def run(self, ctx):
        info = ctx.world_map()
        result = ctx.run_agent(self._agent_prompt(info), max_probes=ctx.remaining())
        sub = result.get("submission")
        if isinstance(sub, list) and len(sub) == info["M"] and all(
                isinstance(c, int) and not isinstance(c, bool) for c in sub):
            return [c % info["K"] for c in sub]
        return self._assemble(info, ctx.observations())

    # ---- the prompt handed to the deployed agent (NEUTRAL: task + protocol, no strategy) ----
    def _agent_prompt(self, info):
        formulas = "\n".join(f"  cell {c['index']}: {c['formula']}" for c in info["cells"])
        M, K, R = info["M"], info["K"], info["R"]
        return (
            f"You are reconstructing {M} hidden cells, indexed 0..{M - 1}. Each cell holds an "
            f"integer color in 0..{K - 1}.\n\n"
            f"Every cell's color is a FIXED, KNOWN function of {R} hidden registers r0..r{R - 1}. "
            f"Each register is an unknown integer in 0..{K - 1}. The per-cell formulas (the world "
            f"map, known to you) are:\n{formulas}\n\n"
            f"You do NOT know the register values -- that is the only hidden information. Probing a "
            f"cell reveals just that cell's color. You have {info['budget']} probes total -- far "
            f"fewer than {M} cells -- so you must infer the rest.\n"
            "Tools:\n"
            "  - probe(index): reveal one cell's color; returns the value and probes remaining.\n"
            "  - submit_map(values): submit a JSON array of every cell's color, in order. Ends the "
            "episode. Call it exactly once before finishing.\n"
            f"Maximize the number of the {M} cells you predict correctly. Act through tools only; "
            "emit no prose between tool calls."
        )

    # ---- fallback assembly (mock path + a malformed submission): place what was observed ----
    def _assemble(self, info, obs):
        if _MOCK_VARIANT == "edited" and obs:
            fill = max(set(obs.values()), key=lambda v: list(obs.values()).count(v))
        else:
            fill = 0
        return [obs.get(i, fill) for i in range(info["M"])]
