# RECORDED ARTIFACT — not part of the running system, kept for the record.
#
# This is the meta agent's (Opus) FIRST harness edit in the Chapter-2 loop on trap-tetra
# (gen_0001, this session), with ONE bug fixed: the reconstruction comprehension used the
# observed value `v` where it meant the candidate register vector `regs`
# (`value(i, v)` -> `value(i, regs)`), which crashed as "'int' object is not iterable" and
# scored the child 0. Everything else is verbatim Opus.
#
# Why it matters: from the seed's conduct alone (it wasted a probe on the trivially-determined
# anchor cell 0), Opus diagnosed the adaptive-submodularity trap, recognized the world is affine
# over GF(K), and moved BOTH inference halves into free Python — an exhaustive probe-SET search
# (span over the field) + a brute force over the K**R register assignments — using the deployed
# agent only as the airgapped probe executor. Bug-fixed, it reaches the belief-MDP oracle: Opus
# wrote the oracle not as a closed-form *formula* (the threshold gate's bar) but as a *search*,
# which is writable whenever the world is small enough to enumerate. So trap-tetra is below the
# *harness* threshold. (WORLD_DESIGN.md -> "The harness substrate".)
"""Chapter-2 task-agent harness: Python-owned probe selection + register solve.

The world is affine: every cell is a PUBLIC linear function of R hidden registers over
Z_K (`ctx.world_map()` gives each cell's `coeffs` and `const`; only the registers are
hidden). Two facts make this a code problem, not an eyeball problem:

  * A probe set determines a cell iff that cell's coeff vector lies in the span (over the
    field Z_K, K prime) of the probed cells' coeff vectors -- so cells far beyond the ones
    probed are computable.
  * The trap (adaptive submodularity): the locally-richest single probe is NOT part of the
    globally-best set. Here the lone r0 pair (cells 0,1) is the fattest single probe but
    stealing a probe for it starves the 4-register clique, which then can't be fully
    solved. Greedy / articulable selection takes the bait; only searching probe SETS wins.

So this harness does both halves in free Python and uses the agent only as the airgapped
probe executor: it picks the probe SET that maximizes determined coverage (exhaustive when
the search is small, greedy otherwise), tells one agent to probe exactly those cells, then
reconstructs every cell by brute-forcing the K^R register assignments consistent with the
observations and predicting each cell's modal value (optimal under a uniform prior --
determined cells fall out as unanimous, undetermined ones get the best guess).

Contract: class Solver with run(self, ctx) -> list[int] (one color per cell). Imports no
world internals; reaches the world only through `ctx`. Assumes K prime (the world uses K=3).
"""

from itertools import combinations, product
from math import comb


class Solver:
    def run(self, ctx):
        info = ctx.world_map()
        M, K, R = info["M"], info["K"], info["R"]
        coeffs = [[c % K for c in cell["coeffs"]] for cell in info["cells"]]
        consts = [cell["const"] % K for cell in info["cells"]]
        budget = min(ctx.remaining(), M)
        probes = self._select(coeffs, K, M, budget)
        # The agent is the airgap: it executes the chosen probes; Python does the rest.
        ctx.run_agent(self._prompt(M, probes), max_probes=len(probes))
        return self._reconstruct(coeffs, consts, ctx.observations(), R, K, M)

    # ---- probe-SET selection: maximize cells whose coeff lies in the probed span --------
    def _select(self, coeffs, K, M, budget):
        if budget <= 0:
            return []

        def determined(rows):
            basis = []
            for r in rows:
                self._add_row(coeffs[r], basis, K)
            return sum(1 for c in coeffs if self._in_span(c, basis, K))

        # Exhaustive over probe sets when feasible -- defeats the submodularity trap that
        # greedy info-gain falls for; falls back to greedy only if the space is large.
        if comb(M, budget) <= 50000:
            best, score = (), -1
            for P in combinations(range(M), budget):
                s = determined(P)
                if s > score:
                    best, score = P, s
            return list(best)
        chosen = []
        while len(chosen) < budget:
            pick, best = None, -1
            for c in range(M):
                if c in chosen:
                    continue
                s = determined(chosen + [c])
                if s > best:
                    pick, best = c, s
            chosen.append(pick)
        return chosen

    # ---- reconstruction: modal cell value over register assignments consistent w/ probes -
    def _reconstruct(self, coeffs, consts, obs, R, K, M):
        obs = {int(i): v for i, v in obs.items()}

        def value(i, regs):
            return (sum(a * r for a, r in zip(coeffs[i], regs)) + consts[i]) % K

        consistent = [
            regs for regs in product(range(K), repeat=R)
            if all(value(i, regs) == obs[i] for i in obs)   # FIX: regs, not the observed value
        ]
        if not consistent:  # unreachable for honest observations; degrade gracefully
            return [obs.get(i, 0) for i in range(M)]
        out = []
        for i in range(M):
            tally = {}
            for regs in consistent:
                v = value(i, regs)
                tally[v] = tally.get(v, 0) + 1
            out.append(max(tally, key=tally.get))
        return out

    # ---- linear algebra over the field Z_K (K prime) ------------------------------------
    def _reduce(self, v, basis, K):
        v = [x % K for x in v]
        for piv, row in basis:
            if v[piv]:
                f = v[piv]
                v = [(a - f * b) % K for a, b in zip(v, row)]
        return v

    def _in_span(self, v, basis, K):
        return not any(self._reduce(v, basis, K))

    def _add_row(self, v, basis, K):
        v = self._reduce(v, basis, K)
        for i, x in enumerate(v):
            if x:
                inv = pow(x, K - 2, K)  # Fermat inverse; K prime
                basis.append((i, [(a * inv) % K for a in v]))
                return

    # ---- the agent is told only which cells to probe (no strategy, no eyeballing) --------
    def _prompt(self, M, probes):
        plist = ", ".join(str(p) for p in probes)
        return (
            f"You are reconstructing {M} hidden cells. Probe EXACTLY these cells, in order, "
            f"one probe each: [{plist}]. Call probe(index) for each, then stop. Do NOT call "
            f"submit_map. Act through tools only; emit no prose."
        )
