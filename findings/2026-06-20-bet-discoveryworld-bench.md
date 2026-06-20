# Finding — the bet, on the bench: DiscoveryWorld + a native Haiku agent (2026-06-20)

The first build of `BET.md`'s experiment: equip a cheap agent with our framing, race it against the
same agent without it, on a world where the path is scored. This is the lab note for *standing the
bench up* — not yet the verdict on the bet (that needs a calibrated multi-seed race).

## What got built (`bet/`)

A native **Claude Code subagent** (a `claude -p` session on Haiku) drives Ai2's **DiscoveryWorld**
through a **confined action interface** — deliberately *not* the HTA MCP probe protocol. The agent's
only tool is Bash locked to one command (`python dw.py`), pointed at a clean workdir holding just the
client; the world lives in a separate server process the agent can't read. Two arms, one toggle:
`playbook.md` (the operating loop + two guards) vs `baseline.md` (a generic competent prompt), shipped
as the agent's system prompt. Everything else is held fixed — that is the experiment.

The integrity floor holds: scoring is a dumb DiscoveryWorld function the agent never sees (the
`scorecard` command is privileged; the client doesn't expose it).

## What we learned (the build, not the bet)

- **DiscoveryWorld runs headless here** (SDL dummy driver), loads a scenario in ~0.2s, and exposes a
  clean path score (`scoreNormalized`, e.g. 8 subgoals on Proteomics/Normal). It clears the
  "score the path, not the answer" bar BET.md insisted on, out of the box.
- **The native-subagent realization works.** A Haiku `claude -p` with Bash confined to the client
  actually played: in a budget-starved 8-move run it picked up the proteomics meter, teleported to an
  animal area, found and analyzed an echojelly (Protein A 0.70 / B 0.75), scouted a second area, and
  stopped when the move budget hit zero. Cost ≈ **$0.11**, ~90s, 12 turns.
- **First datapoint: process = 0.25 (2/8), not zero.** Exactly the "low-but-nonzero" band BET item 2
  asks for — at 8 moves it's clearly budget-starved, so the real race wants ~30–50. The agent even
  reflected (unprompted) on its *allocation* — "I should have budgeted actions" — which is the
  playbook's discipline showing up in behaviour.

## What this does NOT yet show

The lift. One arm, one seed, a starved budget proves the pipe, not the bet. The verdict needs the
calibrated race: pick the difficulty/budget where plain-Haiku is low-but-nonzero, run both arms over
~5 parametric seeds, and read toggle-on minus toggle-off on `process_score`. That's a ~$5–10 run, so
it's a deliberate firing, not an auto-run.

## Open (carried from BET.md)

1. **Playbook prose** — first cut written; tune the *smallest* wording that induces the loop, and
   whether the forecast should be a fixed `EXPECT/OPENS/COST` line vs free text.
2. **Difficulty band** — calibrate to low-but-nonzero plain-Haiku (the seam + scorecard are ready).
3. **Confined interface** — done (soft airgap). Harden to a container if a bulletproof wall is needed.
4. **Run protocol** — multi-seed two-arm + lift report exist; the win margin and N still to set.
