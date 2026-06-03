"""hypertaste: a self-improving research-taste harness.

Three hard-separated planes:
  * WORLD plane  (hta.world)  -- WILT engine + Opus world-smith. Agent-inaccessible.
  * AGENT plane  (hta.task_agent / hta.meta_agent / hta.archive) -- DGM-H self-improvement.
  * TASTE plane  (hta.taste)  -- defines/measures good research behavior -> fitness.

All foundation-model calls funnel through hta.llm (claude -p only).
"""

__version__ = "0.1.0"
