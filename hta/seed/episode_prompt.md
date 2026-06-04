# Episode: discover the hidden rule (Wason 2-4-6)

You are interacting with a hidden rule that maps three numbers (x, y, z) to True or
False. Your goal is to discover the rule and submit it as a Python lambda.

You have up to {max_probes} probes. Available tools:
- probe(x, y, z): test a case; returns the rule's True/False and probes remaining.
- remaining(): how many probes are left.
- submit_guess(rule): submit your final answer as "lambda x, y, z: ..." and end the episode.

Protocol:
1. Call probe() on your FIRST turn — do not preface it with analysis. After each
   result, update which rules are still possible.
2. {strategy_guidance}
3. Do NOT call remaining() — track your probe count yourself; every non-probe turn is
   wasted budget.
4. When you are confident (or low on probes), call submit_guess EXACTLY ONCE with the
   simplest lambda consistent with everything you observed (Occam's razor). You MUST call
   submit_guess before the episode ends, or it counts as no answer.

Act through tools only. Emit no prose between tool calls.
