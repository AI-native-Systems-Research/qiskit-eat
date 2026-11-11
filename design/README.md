# Depth-aware tie-breaks in Sabre — design & validation package

Supporting documents for the `sabre-depth-aware-tiebreaks` change (iteration 1 of the EAT Sabre work).
The code change itself is on branch `sabre-depth-aware-tiebreaks`; this `design/` folder is the docs companion.

| Artifact | File |
|---|---|
| **Presentation** (explains the change) | [`sabre-depth-aware-tiebreaks.pdf`](sabre-depth-aware-tiebreaks.pdf) — 7-slide mechanism walkthrough with a worked example (source: [`change-deck.html`](change-deck.html)) |
| **PR body** | [`PR_BODY.md`](PR_BODY.md) |
| **Issue draft** | [`ISSUE.md`](ISSUE.md) |
| **Validation report** | [`validation-report.md`](validation-report.md) |
| **Validation script** | [`validate.sh`](validate.sh) — reproduces the eval on the CCC evaluator |
| Benchmark deck (results) | [`pr1-benchmark-deck.html`](pr1-benchmark-deck.html) — the numbers, separate from the mechanism presentation |

## One-line result

Breaking Sabre's layout-trial and swap ties by estimated two-qubit depth (instead of arbitrarily) reduces two-qubit
depth **~8.7%** with gate count flat and all correctness checks (C1–C7) passing — official evaluator verdict **PASS**,
the change measured alone against the clean baseline. See the validation report for per-case numbers and scope caveats.

## What's here vs. the full picture

These numbers are the compact `iterations-profile` (3 workloads × cz/cx/ecr × L2 × 100 seeds), which isolates this
single change. The whole-run, 8-family results and the independent Benchpress validation (~6% depth on 18,738
circuits the agents never saw) live with the overall EAT write-up; this package is scoped to the one change on this
branch.
