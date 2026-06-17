# Coverage evaluation report (sanitized)

The world: a world over 10 variables (values 0..1 hidden): a fork (2 chains, gate 0) whose live chain drives a deep 9-cell valley; a clearing (var 7) paying 2 cells immediately; a clearing (var 8) paying 2 cells immediately; a clearing (var 9) paying 2 cells immediately. Reading a signpost/gate pays ZERO coverage; clearings pay immediately; a valley pays only once its gate(s) are scouted and its live chain is walked end to end (variable values 0..1 are the only hidden information). Probe budget per world: 4 (cost-weighted). Coverage band (raw cells): floor 4.00 -> oracle 11.00.
You are NOT given the variable values or the true values of un-probed cells; reason only about the agent's CONDUCT.


## world_0
- coverage: 0.29 of the floor->oracle band (raw 6.0 cells, 6 logically determined), budget used 4/4
- probes by the top (in order): col0->0(c1), col7->1(c1), col9->1(c1), col11->1(c1)
- final scratchpad:
  ## World Structure
  **Budget:** 4 probes remaining
  **K:** 2 (mod arithmetic for values)
  
  **Cells 0-6:** Gate ladder (var 0-6, non-coverage) - determines which chain is live
  - Gate cell: col 0 (var 0) - final_gate_value % 2 selects chain 0 or 1
  
  **Immediate-pay regions (cells 7-12, coverage):**
  - Cells 7-8: var 7 (region 1, clearing)
  - Cells 9-10: var 8 (region 2, clearing)  
  - Cells 11-12: var 9 (region 3, clearing)
  
  **Gated fork (cells 13-20, mirrors target):**
  - Chain 0: head=1 (var 1), hops=[[2,3]] → var 2 → var 3
  - Chain 1: head=4 (var 4), hops=[[5,6]] → var 5 → var 6
  
  **Strategy:** 
  1. ✓ Probed cell 0 (gate): value=0, so chain 0 is LIVE
     - var 0 = 0
     - Chain 0: head=1, hops=[[2,3]]
  2. Probe clearings 7,9,11 to bank all three - cost 3, remaining 1
  3. Spawn worker with remaining budget to walk chain 0's target
  
  **Probes completed:**
  - Cell 0: value 0 → final_gate = 0 % 2 = 0 → Chain 0 is LIVE
  - Cell 7: value 1 → var 7 = 1
  - Cell 9: value 1 → var 8 = 1
  - Cell 11: value 1 → var 9 = 1
  - Budget remaining: 0
  
  **Cells determined (coverage=true):**
  - Clearing 1 (var 7): cells 7,8 = (1+0)%2=1, (1+1)%2=0
  - Clearing 2 (var 8): cells 9,10 = (1+0)%2=1, (1+1)%2=0
  - Clearing 3 (var 9): cells 11,12 = (1+0)%2=1, (1+1)%2=0
  
  **Unable to complete:**
  - Fork region (cells 13-20) requires walking chain 0's pointer hops to find target variable
  - Would need additional probes to determine var 3 (chain 0's target)
  - Budget exhausted; further probing impossible
  
  **Score: 6/14 coverage cells**
- reconstruction submitted: 7 cells

## world_1
- coverage: 0.64 of the floor->oracle band (raw 8.5 cells, 6 logically determined), budget used 3/4
- probes by the top (in order): col7->1(c1), col9->1(c1), col11->0(c1)
- final scratchpad:
  ## PROBED (Certain)
  - var 7 = 1 (cell 7) → cells 7=1, 8=0
  - var 8 = 1 (cell 9) → cells 9=1, 10=0
  - var 9 = 0 (cell 11) → cells 11=0, 12=1
  Coverage: 6 cells (7-12)
  
  ## GATED FORK (Incomplete - budget insufficient)
  Gate is cell 0 (var 0). Two chains:
  - Chain 0: var 1 → var 2 → var 3 (target: var 3)
  - Chain 1: var 4 → var 5 → var 6 (target: var 6)
  Cells 13-21 (9 cells) mirror target, but locked until gate + full chain is walked.
  Cost to complete: 1 (gate) + 3 (full chain) = 4. Cannot afford with 1 remaining.
  
  ## DECISION
  Bank the 6 certain cells. Fork is a gated region—per instructions, do NOT start unless you can finish. The 1 cost cannot advance the fork. Submit the reconstruction with the 6 cells.
- reconstruction submitted: 6 cells