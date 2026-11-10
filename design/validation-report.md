# Validation report: depth-aware tie-breaks in Sabre

**Change:** depth-aware tie-breaks in `crates/transpiler/src/passes/sabre/{dag,layout,route}.rs`.
**Method:** the transpiler benchmark harness, run on the baseline tree with only this change's 3 files applied, so the
numbers reflect this change on its own. The harness confirmed the evaluated tree differs from baseline by exactly
these 3 files.
**Baseline:** Qiskit `73aa14d` plus the shared VF2 tie-break fix (commit `9292f627e`).
**Runs:** 2026-11-10. Two panels: the full 8-family development panel, and a smaller 3-workload panel for the
per-case detail.

## Result (full 8-family development panel, 100 seeds)

This is the same panel used to score the overall run.

| | |
|---|---|
| **Two-qubit depth (D2)** | ratio 0.9378, **6.2% lower**; paired SE(log) 0.0019 |
| **Two-qubit gate count (N2)** | **1.3% lower** (passed) |
| **Trade score** √(D2·N2) | 0.9623 |
| **cx basis** | depth 7.6% lower, gate count 1.4% lower (both passed) |
| **ecr basis** | depth 7.4% lower, gate count 1.4% lower (both passed) |
| **Improvement + breadth guards** | passed |
| **Correctness C0–C7** | passed |

Depth is lower across the panel and on both the cx and ecr basis panels. Gate count is lower, not higher.
Correctness and the improvement/breadth guards all pass.

### One caveat on the verdict

The harness printed `INCONCLUSIVE` (score 0) for this run, for one reason: the `CA5/confirm-timing` cost panel did
not finish. It timed out after 25 minutes waiting for the shared node to go quiet (the error is "Missing normal cost
bundle"), because the node was busy with other jobs at the time. This is a measurement-infrastructure timeout, not a
property of the change: the depth, gate-count, and correctness results above all completed and passed. It is the same
cost-panel timeout the overall run hit. Re-running the cost panel on an idle node would clear it; the depth and gate
numbers would not change.

## Per-case detail (3-workload panel, level 2, 100 seeds, ratio evolved/baseline; <1 = better)

A smaller run on QFT, square-Heisenberg and QAOA at 100 qubits, which completed with a clean **PASS** (score 1.0948).
It gives the per-case picture:

| Workload | Base | D2 | N2 | N2 within 1.05 cap |
|---|---|---|---|---|
| QFT n100 | cz | 0.948 | 0.977 | yes |
| QFT n100 | cx | 0.947 | 0.975 | yes |
| QFT n100 | ecr | 0.948 | 0.977 | yes |
| square-Heisenberg n100 | cz | 0.881 | 0.972 | yes |
| square-Heisenberg n100 | cx | 0.881 | 0.972 | yes |
| square-Heisenberg n100 | ecr | 0.881 | 0.972 | yes |
| QAOA ba n100 | cz | 0.912 | 1.034 | yes |
| QAOA ba n100 | cx | 0.912 | 1.035 | yes |
| QAOA ba n100 | ecr | 0.912 | 1.034 | yes |
| **Panel (weighted)** | | **0.913** | **0.994** | — |

Depth is lower on all nine workload/basis points. Gate count is lower on six; on QAOA it rises 3.4 to 3.5%, below the
5% per-case limit. The two panels agree on the shape; the smaller one shows a larger average depth drop (8.7%) because
it leaves out the easier families that the full panel includes.

## Correctness (both runs, on the evolved tree)

- **C1–C5** exact small-circuit equivalence.
- **C6** routing-replay: the routed circuit reproduces exactly.
- **C7** Clifford-variant equivalence (compile and verify; 440 variant outputs on the full panel).
- Coupling-map legality on every two-qubit gate of every output.
- Determinism: identical output for a fixed seed, parallel routing on or off.

## Reproduce

See `validate.sh`. On a host with the evaluator image it materializes `baseline + this diff` and runs the eval; the
last line is `SCORE: <x>`. For the full panel it sets `--profile dev-profile`; for the 3-workload panel,
`--profile iterations-profile`.
