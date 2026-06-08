"""hypertaste: a self-improving research-taste harness (DGM-H pipeline).

Three hard-separated planes (Chapter 2, post-reset -- see RESET_DESIGN.md):
  * WORLD plane  (hta.ch2)               -- the anchor world + coverage oracle. Agent-inaccessible.
  * AGENT plane  (hta.meta_agent / hta.archive) -- DGM-H self-improvement of the playbook node.
  * TASTE plane  (hta.taste)             -- the MDL / program-length generality prior.

All foundation-model calls funnel through hta.llm (claude -p only).
"""

__version__ = "0.1.0"
