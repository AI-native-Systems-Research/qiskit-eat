# Sabre breaks layout and routing ties arbitrarily, leaving two-qubit depth on the table

## Summary

Sabre's layout and routing stages repeatedly choose among options its own scoring rates as **equal**, and today it
resolves those ties arbitrarily: by lowest trial index for layout trials, and by uniform-random pick for swaps.
Arbitrary tie-breaking throws away a free lever: among equally-scored options there is usually one that routes the
circuit's two-qubit gates in fewer layers, i.e. at lower two-qubit depth.

## Where it happens

1. **Layout-trial selection** (`crates/transpiler/src/passes/sabre/layout.rs`). Sabre runs several layout trials and
   keeps `min_by_key(swap_count, trial_index)`. When two trials tie on swap count, the lower index wins, which is
   unrelated to circuit quality.
2. **Swap selection during routing** (`crates/transpiler/src/passes/sabre/route.rs`). For look-ahead heuristics, when
   several candidate swaps share the best heuristic score, the choice among them is uniform-random.

In both places the tie-break is blind to the resulting two-qubit depth.

## Impact

On the development panel (QFT / square-Heisenberg / QAOA at 100 qubits, 100 seeds, level 2), making both tie-breaks
depth-aware reduces weighted two-qubit depth **~8.7%** with two-qubit gate count flat (−0.6%) and all correctness
checks (C1–C7) passing. Depth improves on every case measured. See `design/validation-report.md`.

## Proposed change

Break both ties by estimated two-qubit depth, keeping swap count as the primary key so swap count (and thus gate
count) cannot regress:

- Layout trials: select by `(swap_count, estimated_two_qubit_depth, trial_index)`.
- Swaps: among those tied for the best heuristic score, keep the ones whose deeper qubit ends up shallowest, then fall
  back to the existing random choice.

Because this only reorders options already judged equal on swap cost, it does not add swaps. It replaces blind
tie-breaking with depth-reducing tie-breaking. On by default, no new public API.

## Scope / non-goals

- Confined to the Sabre pass (3 source files, +159/−6); no change to which trials are generated, which swaps are
  considered, any heuristic score, or any preset pass manager.
- Not a new heuristic or a tuning knob — a strictly-better tie-break on the existing path.

## Acceptance

- Correctness C1–C7 pass; coupling-map legality preserved; deterministic for a fixed seed.
- Two-qubit gate count not worse than baseline beyond noise, and no per-case N2 above the 1.05× cap.
- Measured two-qubit depth reduction on the panel.

Proposed PR: branch `sabre-depth-aware-tiebreaks`.
