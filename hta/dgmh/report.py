"""The sanitized conduct report -- the meta-side airgap wall.

The meta-agent rewrites the playbook from a report of *how the play went*. This module builds
that report, and it is where the integrity floor is physically enforced on the meta side: the
report carries the player's own conduct (which probes, which workers, the scratchpad) and the
world's *public* face, but NEVER the hidden answer or any un-probed true value.

It is the meta-side dual of the play-side tool confinement (hta/dgmh/play/server.py): one wall
keeps hidden state off the player's channel, this one keeps it off the meta-agent's. Because
redaction must know what is hidden, draw the public/hidden line from the world's public face
only -- never read the run log's hidden fields here.

Stub: the report builder lands when LOOP 1 is wired (the reference is the sanitizer in
hta/_trail/loop.py). This is a security seam -- keep the strip logic in this one auditable file.
"""

from __future__ import annotations


def build_report(play: object) -> str:
    """Build the sanitized conduct report for the meta-agent. Public face + conduct only.

    Must not surface the hidden answer or any un-probed true value.
    """
    raise NotImplementedError("the redaction logic lands when LOOP 1 is wired")
