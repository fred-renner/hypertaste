# Coverage evaluation report (sanitized)

The world: a world over 10 variables (values 0..1 hidden): a fork (2 chains, gate 0) whose live chain drives a deep 9-cell valley; a clearing (var 7) paying 2 cells immediately; a clearing (var 8) paying 2 cells immediately; a clearing (var 9) paying 2 cells immediately. Reading a signpost/gate pays ZERO coverage; clearings pay immediately; a valley pays only once its gate(s) are scouted and its live chain is walked end to end (variable values 0..1 are the only hidden information). Probe budget per world: 4 (cost-weighted). Coverage band (raw cells): floor 4.00 -> oracle 11.00.
You are NOT given the variable values or the true values of un-probed cells; reason only about the agent's CONDUCT.


## world_0
- coverage: 0.14 of the floor->oracle band (raw 5.0 cells, 4 logically determined), budget used 4/4
- probes by the top (in order): col0->1(c1), col6->0(c1), col7->1(c1), col9->1(c1)
- final scratchpad:
  === WORLD STRUCTURE ===
  Budget: 4 (SCARCE - each probe costs 1)
  K = 2, R = 10 variables
  
  REGIONS:
  - Region 0 (FORK): gate=var0, chains: [1→2→3] or [4→5→6], selects by var0 mod 2
  - Regions 1-3 (CLEARINGs): var7 (length 2), var8 (length 2), var9 (length 2)
  
  COVERAGE CELLS (what we score on):
  - Cols 7-12: vars 7,8,9 in clearings (PROBEABLE)
  - Cols 13-21: fork region (NOT probeable - must reconstruct via chain walking)
  
  STRATEGY:
  With budget 4, I must:
  1. Probe var0 (gate) - determines which chain is live
  2. Follow that chain's path to determine the target variable
  3. Reconstruct fork cells based on target variable's value
  
  PROBES TAKEN:
  1. var0 = 1 (cost 1) → selects chain[1]: var4→var5→var6
  2. var6 = 0 (cost 1) → target value
  
  RECONSTRUCTED (fork cells, cols 13-21):
  var6=0, so each cell = (0 + pos) mod 2
  - Alternating pattern: 0,1,0,1,0,1,0,1,0
  
  FINAL PROBES:
  3. var7 = 1 (cost 1) → cols 7-8: (1+0)%2=1, (1+1)%2=0
  4. var8 = 1 (cost 1) → cols 9-10: (1+0)%2=1, (1+1)%2=0
  
  BUDGET EXHAUSTED: remaining = 0
  
  COVERAGE CELLS (certain):
  - col 7: 1 (var7=1, pos=0)
  - col 8: 0 (var7=1, pos=1)
  - col 9: 1 (var8=1, pos=0)
  - col 10: 0 (var8=1, pos=1)
  - cols 13-21: 0,1,0,1,0,1,0,1,0 (var6=0 chain)
  
  UNCERTAIN (must guess):
  - col 11-12: var9 unknown (0 or 1)
- reconstruction submitted: 15 cells

## world_1
- coverage: 0.00 of the floor->oracle band (raw 4.0 cells, 4 logically determined), budget used 4/4
- probes by the top (in order): col0->1(c1), col6->1(c1), col9->1(c1), col11->1(c1)
- final scratchpad:
  ## Investigation Log
  
  **World Structure:**
  - Budget: 4 probes
  - Coverage cells: cols 7-21 (vars 7, 8, 9 + fork region)
  - Fork gate at var 0; chains select which target variable to mirror
  - Chain 0: regions 1→2→3, target likely var 9
  - Chain 1: regions 4→5→6, target unknown
  
  **Strategy:**
  1. Probe gate (col 0) to determine live chain
  2. Based on chain, determine target variable
  3. Probe target variable + vars 8,9 to cover all coverage cells
  4. Reconstruct fork cells from target value
  
  **Probes:**
  1. Col 0 (var 0, pos 0): value=1 → var_0_hidden = 1
  2. Col 6 (var 6, pos 0): value=1 → var_6_hidden = 1
  3. Col 9 (var 8, pos 0): value=1 → var_8_hidden = 1
  4. Col 11 (var 9, pos 0): value=1 → var_9_hidden = 1
  
  **Reconstructed Values:**
  - Gate (var 0): value 1 → Chain 1 is LIVE
  - Target var (var 6): hidden=1
  - Var 8: hidden=1
  - Var 9: hidden=1
  
  **Coverage cells reconstructed:**
  - Col 0: (1+0) mod 2 = 1 ✓
  - Col 6: (1+0) mod 2 = 1 ✓
  - Col 9: (1+0) mod 2 = 1 ✓
  - Col 10: (1+1) mod 2 = 0
  - Col 11: (1+0) mod 2 = 1 ✓
  - Col 12: (1+1) mod 2 = 0
  - Cols 13-21 (fork, mirror var 6):
    - Col 13-21: alternating 1,0,1,0,1,0,1,0,1
    
  **Missing:** Var 7 (cols 7-8) - no budget remaining**
- reconstruction submitted: 15 cells