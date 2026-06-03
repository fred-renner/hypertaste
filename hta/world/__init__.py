"""WORLD plane -- AGENT-INACCESSIBLE.

The hidden rule and the scorer live here and are *never* importable from the
agent's editable surface. The agent reaches the world only through
hta.world.channel.ProbeChannel (boolean probe results only).
"""
