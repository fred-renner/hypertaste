Investigate a hidden world under a scarce probe budget. You can probe cells, deploy workers with a
share of your budget and a task you write, keep an editable scratchpad, and submit one
reconstruction. Spend your budget well; reconstruct as much of the world as you can.

Some payoffs are immediate — one probe pins what it pays. Others are deferred behind prerequisites:
a big payoff that pays only once a whole sequence of cells has been probed end to end, where the
prerequisite cells (gates, signposts, intermediate steps) pay nothing on their own. A deferred
payoff is all-or-nothing — a half-walked sequence pays exactly zero, so every probe you spent
getting partway is wasted, and you cannot infer the unprobed remainder from the part you did probe.

So before you spend the first probe on a deferred payoff, count its full unlock-cost — every
prerequisite plus the final step — and check that it fits your remaining budget. Commit only if you
can finish the whole sequence; otherwise leave it untouched and spend on payoffs that pay per probe.
Never strand budget halfway down a sequence.

Keep the scratchpad as a running ledger, not a plan you wrote once. For each payoff list its
unlock-cost, whether you have committed to it, and what it has actually paid so far; track remaining
budget and update it after every probe. Only count a deferred payoff as covered once its sequence is
truly complete — never bank cells you merely reconstructed.
