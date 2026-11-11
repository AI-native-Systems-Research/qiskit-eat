# SABRE depth-aware tie-break — layout and routing validation

**PASS** — 48/48 paired cases correct on both builds; routing changed in 48/48.

Evolved: Qiskit 2.7.0.dev0 (the EAT 1.323 tree, which contains this change). Baseline: Qiskit 2.7.0.dev0 (73aa14d). Seeds: [0, 1, 42, 2, 7, 123]. Run: 2026-11-11T08:30:42.723341+00:00.

Each 10-qubit circuit is routed on a bidirectional line with SABRE layout+routing under both builds. A case passes when the routed output keeps its width, carries layout metadata, places every two-qubit gate on a coupling-map edge, and matches the original unitary (layout-aware, global phase kept, default tolerances).

| Circuit | Both correct | Routing changed |
|---|---|---|
| qft10 | 6/6 | 6/6 |
| random10x20 | 6/6 | 6/6 |
| random10x40 | 6/6 | 6/6 |
| random10x60 | 6/6 | 6/6 |
| ring10 | 6/6 | 6/6 |
| qv10 | 6/6 | 6/6 |
| qv10_seed7 | 6/6 | 6/6 |
| alltoall10 | 6/6 | 6/6 |
| **All** | **48/48** | **48/48** |

Self-checks (negative controls on the evolved build; each passes only if the deliberately broken circuit no longer matches the reference):
- extra_x_must_fail: PASS
- ignored_final_layout_must_fail: PASS

Scope: layout/routing correctness and observable routing changes on these circuits and seeds. Not a general correctness proof. The evolved arm is the full 1.323 stack; the isolated tie-break additionally passes the task harness's C1–C5 exact-equivalence suite.
