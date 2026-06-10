# sample-mock — the curated sample run (PLAN.md Pass 0)

Generated 2026-06-10 by:

```bash
python run_loop.py --iterations 2 --backend mock --out-dir runs/sample-mock
```

Mock backend: free, deterministic (the floor-player, not a model of taste) — these artifacts
demonstrate the run record's shape, not a result. What each file is:

- `archive/gen_XXXX/` — the lineage: each node's `playbook.md` (the evolved English),
  `node.json` (fitness summary), and the sanitized `EVAL_REPORT.md` its meta-edit saw.
- `iter_XXXX.json` — the per-iteration audit record: spec, the hidden draws, parent/child
  evals with **full episode transcripts** (every probe, spawn, scratchpad, submission).
  Replayable: `loop.score_result(spec, hstar, result)` reproduces any persisted score.
- `run.json` — invocation args, per-iteration outcomes, `claude -p` call/cost accounting.
