# Validation report — depth-aware tie-breaks in Sabre

**Change:** iteration-1 depth-aware tie-breaks (`crates/transpiler/src/passes/sabre/{dag,layout,route}.rs`).
**Method:** official transpiler evaluator (`eval_official.sh`), the same harness used to score every EAT iteration,
run on the clean baseline with **only this change's 3 files applied** — so the measured effect is this change alone,
not bundled with later iterations.
**Baseline:** Qiskit `73aa14d` + the shared VF2 tie-break fix (commit `9292f627e`).
**Panel:** official `iterations-profile` — QFT, square-Heisenberg and QAOA at 100 qubits, on cz / cx / ecr bases,
optimization level 2, **100 transpilation seeds per case**.
**Run:** CCC, 2026-11-10.

## Verdict

| | |
|---|---|
| **Verdict** | **PASS** |
| **Score** (1 / D2 ratio) | **1.094834** |
| **D2 ratio** (evolved/baseline) | 0.9133806516 — **−8.66% two-qubit depth** |
| **D2 paired SE(log)** | 0.005087 |
| **N2 primary** (two-qubit gate count) | −0.63% — **flat, passed** |
| **Trade score** √(D2·N2) | 0.9527 |
| **Scope confirmed by harness** | 3 changed, 0 added, 0 deleted |

## Per-case results (level 2, 100 seeds, ratio evolved/baseline; <1 = better)

| Workload | Base | D2 | N2 | N2 cap (≤1.05) |
|---|---|---|---|---|
| QFT n100 | cz | 0.948 | 0.977 | pass |
| QFT n100 | cx | 0.947 | 0.975 | pass |
| QFT n100 | ecr | 0.948 | 0.977 | pass |
| square-Heisenberg n100 | cz | 0.881 | 0.972 | pass |
| square-Heisenberg n100 | cx | 0.881 | 0.972 | pass |
| square-Heisenberg n100 | ecr | 0.881 | 0.972 | pass |
| QAOA ba n100 | cz | 0.912 | 1.034 | pass |
| QAOA ba n100 | cx | 0.912 | 1.035 | pass |
| QAOA ba n100 | ecr | 0.912 | 1.034 | pass |
| **Panel (weighted)** | | **0.913** | **0.994** | — |

D2 improves on all nine case×base points. N2 improves on six; on QAOA it rises +3.4–3.5%, within the harness's
1.05× per-case cap, so it is not a gate that fails. The net N2 is −0.6% (flat).

## Correctness (all pass on the evolved tree)

- **C1–C5** exact small-circuit equivalence (480-configuration frozen regression suite).
- **C6** routing-replay — the routed circuit reproduces exactly.
- **C7** Clifford-variant equivalence (compile + verify).
- Coupling-map legality on every two-qubit gate of every output.
- Determinism: identical output for a fixed seed, parallel routing on or off.

Constraint families evaluated and passed: IA1 (legality) ×7, IA2 (improvement), IA3 (primary D2/N2 + cx/ecr basis
panels) ×6, IA4 (per-case D2/N2 caps) ×21, IA5 ×3, IA6, audit, baseline, harness.

## Honest scope

- This is the compact `iterations-profile` (3 workloads), chosen to isolate this single change quickly. It is **not**
  the full 8-family (G1–G8) dev panel; a full-panel re-run would add the per-family breakdown but is not required to
  establish this change's isolated effect.
- Development-panel result on one task (two-qubit depth) and one metric family. It is the first of five stacked EAT
  changes; each will be benchmarked the same way on its own branch.

## Reproduce

See `design/validate.sh`. On a host with the evaluator image (CCC), it materializes `baseline + this diff` and runs
`eval_official.sh`; the last line is `SCORE: <x>`.
