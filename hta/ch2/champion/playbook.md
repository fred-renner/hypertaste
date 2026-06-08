Reconstruct a hidden world under a scarce probe budget. You can probe cells, deploy workers with a
share of your budget and a task you write, keep an editable scratchpad for this world, and submit
once. Investigate well; reconstruct as much as you can.

Reconstruction is a deterministic lookup, not a pattern to guess (read `world_map`'s `value_rule`):
a cell becomes knowable exactly when your probes have pinned its register, and then its value is
forced. When you submit, give the forced value for every cell you can determine this way, and do not
submit a value for any cell whose register you have not pinned — an unpinned guess earns nothing and
only dilutes the answer.

Allocation — where your scarce probes go. The big payoff is the deep valley, and it pays only once
you have walked a full chain of signposts to its landmark and pinned that register; the clearing
blocks pay a little immediately but they sit off the trail, so do not let them eat your budget. List
every chain the `world_map` offers, count the coverage each would pay against the probes it costs to
walk, and commit your budget to the deepest chain — walk it end to end so the valley flips on. Then
reconstruct the valley and every register you pinned along the way.
