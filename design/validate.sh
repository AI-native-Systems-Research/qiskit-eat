#!/usr/bin/env bash
# Reproduce the standalone validation of the depth-aware tie-break change.
#
# It builds a Qiskit tree = the clean baseline (73aa14d + the shared VF2 fix) with ONLY this change's
# Sabre files applied, then runs the official transpiler evaluator against the frozen baseline build.
# The last line printed is "SCORE: <x>"; a PASS verdict means 1 / D2 ratio, else 0.
#
# This is the same harness that scored every EAT iteration. It needs the evaluator environment
# (coordinator venv, base-tree, wheelhouse, rust toolchain) that lives on the CCC run node — it is not
# a laptop script. On CCC, submit it as a pinned job on the node that holds /var/tmp/eat-qiskit-*.
#
# Usage:  EAT_ROOT=/var/tmp/eat-qiskit-20261101 bash validate.sh /path/to/this/change.diff
set -uo pipefail

R=${EAT_ROOT:?set EAT_ROOT to the evaluator root, e.g. /var/tmp/eat-qiskit-20261101}
DIFF=${1:?usage: validate.sh <change.diff>}      # the 3-file Sabre diff from baseline
RO=$R/ro
E=$R/eval
BASE=9292f627e                                    # 73aa14d + VF2 fix (the EAT baseline)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WT=$E/trees/validate-$STAMP
TAG=validate_$STAMP

# the evaluator's coordinator venv is referenced as $E/coordinator; relink if the scratch GC removed it
[ -e "$E/coordinator/bin/python" ] || ln -sfn "$RO/qtb-coordinator" "$E/coordinator"

# materialize baseline + this change only
rm -rf "$WT"
git -C "$R/task" worktree add -q --detach "$WT" "$BASE"
git -C "$WT" apply --check "$DIFF" || { echo "diff does not apply on $BASE"; echo "SCORE: 0"; exit 1; }
git -C "$WT" apply "$DIFF"
echo "changed files (expect exactly the Sabre source files):"
git -C "$WT" diff --stat -- crates qiskit

# run the official evaluator (compile -> quality -> correctness -> cost -> decide)
EAT_EVAL_WORKERS=${EAT_EVAL_WORKERS:-8} bash "$RO/bench/eval_official.sh" "$WT" "$TAG"

# cleanup
git -C "$R/task" worktree remove --force "$WT" 2>/dev/null || true
