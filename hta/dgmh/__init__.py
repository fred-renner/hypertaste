"""LOOP 1 -- grow the AGENT.

The agent self-improvement loop (DGM-H): the archive + parent selection + the
program-length prior (archive.py), the meta-agent world-airgap (sandbox.py), the episode (the
task agent's play + the probe airgap, in episode/), and the world-agnostic iteration loop
(loop.py). See DESIGN.md.
"""
