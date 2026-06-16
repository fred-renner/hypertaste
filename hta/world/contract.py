"""The World contract -- the interface a world implements.

DEFERRED to the next pass. The real interface (hidden-state realization, the dumb
deterministic scorer, the mechanical oracle/band) is designed from DESIGN.md's principles
-- not from the retired trail's shape. For now this is an empty Protocol so the package
imports and the tree runs through.
"""

from typing import Protocol


class World(Protocol):
    """Placeholder for the world interface; methods land in the next pass."""
    ...
