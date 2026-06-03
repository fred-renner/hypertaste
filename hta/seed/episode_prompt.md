# Episode: discover the hidden rule (Wason 2-4-6)

You are interacting with a hidden rule that maps three numbers (x, y, z) to True or
False. Your goal is to discover the rule and submit it as a Python lambda.

You have up to {max_probes} probes. Available tools:
- probe(x, y, z): test a case; returns the rule's True/False and probes remaining.
- remaining(): how many probes are left.
- submit_guess(rule): submit your final answer as "lambda x, y, z: ..." and end the episode.

Protocol:
1. Use probe() to gather evidence over multiple turns. After each result, update which
   rules are still possible.
2. {strategy_guidance}
3. When you are confident (or low on probes), call submit_guess EXACTLY ONCE with the
   simplest lambda consistent with everything you observed (Occam's razor). You MUST call
   submit_guess before the episode ends, or it counts as no answer.

Use the tools to act; keep any prose to a minimum.
