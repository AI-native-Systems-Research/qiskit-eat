# Sabre: break ties by two-qubit depth in layout-trial and swap selection

## What this changes

Sabre has two places where it picks between options that its own scoring treats as equal:

1. When it selects the best layout trial, several trials can finish with the same swap count. It currently keeps the
   one with the lowest trial index.
2. When it picks the next swap during routing, several candidate swaps can share the best heuristic score. It
   currently picks one of them at random.

In both cases the choice is arbitrary. This PR makes it pick, among the tied options, the one that gives the lower
two-qubit depth.

Swap count stays the primary key for layout-trial selection, and the swap tie-break only reorders swaps that already
share the best score. So the number of swaps Sabre inserts does not change, which means two-qubit gate count does not
change. Only the depth of the result changes.

The change is on by default. There is no new argument or configuration.

## How it works

**Layout-trial selection** (`layout.rs`). The selection key changes from `(swap_count, trial_index)` to
`(swap_count, estimated_two_qubit_depth, trial_index)`. The depth estimate replays the trial's routed gate order once
and counts a SWAP as three two-qubit gates. `route.rs` computes it (`selection_key`), and `dag.rs` stores the
two-qubit-gate count of each node (`num_2q`) so the replay does not have to recount.

**Swap tie-break** (`route.rs`). During routing, Sabre tracks the two-qubit depth reached on each physical qubit (a
circuit two-qubit gate adds a layer; a SWAP only synchronises its two qubits). Among the swaps tied for the best
heuristic score, it keeps the ones whose deeper qubit is shallowest, then uses the existing random choice to break any
remaining tie. The depth tracking is undone by the same rollback Sabre already uses for its release valve.

## Files

```
crates/transpiler/src/passes/sabre/dag.rs      13 +-   SabreNode.num_2q
crates/transpiler/src/passes/sabre/layout.rs    6 +-   trial selection key
crates/transpiler/src/passes/sabre/route.rs   146 +-   depth tracking, selection_key, swap tie-break
```
159 insertions, 6 deletions. Plus a release note and tests in `test/python/transpiler/test_sabre_swap.py`.

## Results

Measured with Qiskit's transpiler benchmark harness, comparing this change against the same tree without it, 100
transpilation seeds per case. Workloads: QFT, square-Heisenberg and QAOA at 100 qubits, on the cz, cx and ecr bases,
at optimization level 2.

- Two-qubit depth: 8.7% lower (ratio 0.913).
- Two-qubit gate count: 0.6% lower, i.e. unchanged within seed-to-seed variation. No individual case rose by more
  than 5%.
- Depth improved on all nine workload/basis combinations. The largest was square-Heisenberg at 11.9%.

Correctness: the harness's equivalence checks all pass on the routed circuits (exact small-circuit equivalence,
routing replay, and Clifford-variant equivalence). Every two-qubit gate in every output is on a coupling-map edge, and
output is identical for a fixed seed whether or not parallel routing is enabled.

Per-case numbers and the exact eval invocation are in `validation-report.md`, and `validate.sh` reproduces the run.

## Notes

- These numbers are from a three-workload panel, not Qiskit's full benchmark suite. They establish the effect of this
  change in isolation. A wider run would give a per-family breakdown but is not needed to see what the tie-break does.
- The two commits in the history are `2bba19308` (layout-trial key) and `f289d996a` (swap tie-break).
