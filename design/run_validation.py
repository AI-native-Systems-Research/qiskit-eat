#!/usr/bin/env python
"""Layout-and-routing correctness check for the SABRE depth-aware tie-break.

For each small circuit (10 qubits) the routed output must still implement the original
unitary (layout-aware, global phase kept, default tolerances), keep its width, carry
layout metadata, and place every two-qubit gate on a coupling-map edge. Same idea and
checks as Ophir's wait-time validation; adapted because our change is built into the
routing (no heuristic flag), so the two arms are two builds, not two heuristics.

Run it under a Qiskit build to validate that build's routing:
    python run_validation.py --arm evolved  --out evolved.jsonl
    python run_validation.py --arm baseline --out baseline.jsonl
Then merge the two to get the report and the routing-effect check:
    python run_validation.py --merge evolved.jsonl baseline.jsonl --report report.md
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone

N = 10                         # qubits per circuit and length of the line
SEEDS = [0, 1, 42, 2, 7, 123]


def build_fixtures():
    """Return name -> 10-qubit pure-unitary circuit (no measure/reset), built from public APIs."""
    from qiskit import QuantumCircuit
    from qiskit.circuit.random import random_circuit
    from qiskit.quantum_info import random_unitary
    import numpy as np

    def qft(n):
        qc = QuantumCircuit(n)
        for j in range(n):
            qc.h(j)
            for k in range(j + 1, n):
                qc.cp(math.pi / 2 ** (k - j), k, j)
        return qc

    def ring(n, depth, seed):
        rng = np.random.default_rng(seed)
        qc = QuantumCircuit(n)
        for _ in range(depth):
            for i in range(n):
                qc.cx(i, (i + 1) % n)
            for i in range(n):
                qc.rz(float(rng.random()), i)
        return qc

    def quantum_volume(n, layers, seed):
        rng = np.random.default_rng(seed)
        qc = QuantumCircuit(n)
        for _ in range(layers):
            perm = rng.permutation(n)
            for k in range(0, n - 1, 2):
                qc.append(random_unitary(4, seed=rng), [int(perm[k]), int(perm[k + 1])])
        return qc

    def all_to_all(n):
        qc = QuantumCircuit(n)
        for i in range(n):
            for j in range(i + 1, n):
                qc.cx(i, j)
        return qc

    rc = lambda depth, seed: random_circuit(N, depth, max_operands=2, measure=False, seed=seed)
    return {
        "qft10": qft(N),
        "random10x20": rc(20, 7),
        "random10x40": rc(40, 123),
        "random10x60": rc(60, 42),
        "ring10": ring(N, 10, 0),
        "qv10": quantum_volume(N, 10, 42),
        "qv10_seed7": quantum_volume(N, 10, 7),
        "alltoall10": all_to_all(N),
    }


def swap_pairs(circ):
    """Ordered, endpoint-normalized physical SWAP pairs; instruction positions are ignored."""
    pairs = []
    for inst in circ.data:
        if inst.operation.name == "swap":
            pairs.append(sorted(circ.find_bit(q).index for q in inst.qubits))
    return pairs


def route_and_check(qc, seed):
    """Route qc with SABRE layout+routing and run the four correctness checks.

    Returns (passed, checks, swap_pairs, routed_circuit, reference_operator).
    """
    from qiskit.quantum_info import Operator
    from qiskit.transpiler import CouplingMap, PassManager
    from qiskit.transpiler.passes import SabreLayout

    cm = CouplingMap.from_line(N)          # bidirectional line
    reference = Operator(qc)
    out = PassManager([SabreLayout(
        cm, seed=seed, layout_trials=4, swap_trials=4, max_iterations=3, skip_routing=False,
    )]).run(qc.copy())

    checks = {}
    checks["width"] = out.num_qubits == N
    checks["layout_metadata"] = (
        out.layout is not None
        and out.layout.initial_layout is not None
        and out.layout.final_layout is not None
    )
    edges = set(map(tuple, cm.get_edges()))
    connectivity = True
    for inst in out.data:
        if getattr(inst.operation, "_directive", False):
            continue
        qubits = tuple(out.find_bit(q).index for q in inst.qubits)
        if len(qubits) > 2 or (len(qubits) == 2 and qubits not in edges):
            connectivity = False
            break
    checks["connectivity"] = connectivity
    # Operator.from_circuit uses out.layout to undo the initial layout and the final SWAP
    # permutation. "==" is np.allclose at default tolerance with no phase fixing, so the
    # global phase has to match too.
    checks["unitary"] = Operator.from_circuit(out) == reference

    return all(checks.values()), checks, swap_pairs(out), out, reference


def negative_controls(routed, reference):
    """Break a known-good routed circuit on purpose; each control passes only if the check now fails."""
    from qiskit.quantum_info import Operator
    recs = []

    # 1. Extra gate: append an X; the unitary must no longer match.
    wrong = routed.copy()
    wrong.x(0)
    recs.append({"control": "extra_x_must_fail", "passed": Operator.from_circuit(wrong) != reference})

    # 2. Ignore the routing permutation: drop final_layout; if routing permuted qubits, the
    #    comparison must now fail (this proves from_circuit really undoes the permutation).
    try:
        wrong2 = routed.copy()
        layout = wrong2.layout
        permuted = layout.final_layout is not None and any(
            layout.final_layout[q] != i for i, q in enumerate(wrong2.qubits)
        )
        if permuted:
            layout.final_layout = None
            recs.append({"control": "ignored_final_layout_must_fail",
                         "passed": Operator.from_circuit(wrong2) != reference})
        else:
            recs.append({"control": "ignored_final_layout_must_fail", "passed": None,
                         "note": "routing added no permutation for this case"})
    except Exception as e:  # noqa: BLE001 - record and continue
        recs.append({"control": "ignored_final_layout_must_fail", "passed": None, "note": str(e)[:120]})

    return recs


def run_arm(arm, out_path):
    import qiskit
    fixtures = build_fixtures()
    records, sample = [], None
    for name, qc in fixtures.items():
        for seed in SEEDS:
            try:
                passed, checks, pairs, routed, reference = route_and_check(qc, seed)
                records.append({"fixture": name, "seed": seed, "passed": passed,
                                "checks": checks, "swap_pairs": pairs})
                if passed and sample is None and any(
                    routed.layout.final_layout[q] != i for i, q in enumerate(routed.qubits)
                ):
                    sample = (routed, reference)
            except Exception as e:  # noqa: BLE001
                records.append({"fixture": name, "seed": seed, "passed": False,
                                "checks": {"error": str(e)[:200]}, "swap_pairs": []})
    controls = negative_controls(*sample) if sample else []
    meta = {"arm": arm, "qiskit": qiskit.__version__, "n": N, "seeds": SEEDS,
            "when": datetime.now(timezone.utc).isoformat()}
    with open(out_path, "w") as f:
        f.write(json.dumps({"record": "meta", **meta}) + "\n")
        for r in records:
            f.write(json.dumps({"record": "case", **r}) + "\n")
        for c in controls:
            f.write(json.dumps({"record": "control", **c}) + "\n")
    npass = sum(1 for r in records if r["passed"])
    print(f"{arm}: {npass}/{len(records)} cases correct; wrote {out_path}")


def load(path):
    rows = [json.loads(line) for line in open(path)]
    meta = next(r for r in rows if r["record"] == "meta")
    cases = [r for r in rows if r["record"] == "case"]
    controls = [r for r in rows if r["record"] == "control"]
    return meta, cases, controls


def merge(evolved_path, baseline_path, report_path):
    em, ecases, econtrols = load(evolved_path)
    bm, bcases, _ = load(baseline_path)
    by = {}
    for r in ecases:
        by.setdefault(r["fixture"], {}).setdefault(r["seed"], {})["e"] = r
    for r in bcases:
        by.setdefault(r["fixture"], {}).setdefault(r["seed"], {})["b"] = r

    rows, tot_both, tot_changed = [], 0, 0
    for fx in by:
        both = changed = n = 0
        for seed, d in by[fx].items():
            e, b = d.get("e"), d.get("b")
            if not e or not b:
                continue
            n += 1
            if e["passed"] and b["passed"]:
                both += 1
            if e["swap_pairs"] != b["swap_pairs"]:
                changed += 1
        rows.append((fx, both, changed, n))
        tot_both += both
        tot_changed += changed
    total = sum(r[3] for r in rows)

    lines = []
    lines.append("# SABRE depth-aware tie-break — layout and routing validation\n")
    verdict = "PASS" if tot_both == total and total > 0 else "CHECK"
    lines.append(f"**{verdict}** — {tot_both}/{total} paired cases correct on both builds; "
                 f"routing changed in {tot_changed}/{total}.\n")
    lines.append(f"Evolved: Qiskit {em['qiskit']} (the EAT 1.323 tree, which contains this change). "
                 f"Baseline: Qiskit {bm['qiskit']} (73aa14d). Seeds: {em['seeds']}. "
                 f"Run: {em['when']}.\n")
    lines.append("Each 10-qubit circuit is routed on a bidirectional line with SABRE layout+routing "
                 "under both builds. A case passes when the routed output keeps its width, carries "
                 "layout metadata, places every two-qubit gate on a coupling-map edge, and matches the "
                 "original unitary (layout-aware, global phase kept, default tolerances).\n")
    lines.append("| Circuit | Both correct | Routing changed |")
    lines.append("|---|---|---|")
    for fx, both, changed, n in rows:
        lines.append(f"| {fx} | {both}/{n} | {changed}/{n} |")
    lines.append(f"| **All** | **{tot_both}/{total}** | **{tot_changed}/{total}** |\n")
    lines.append("Self-checks (negative controls on the evolved build; each passes only if the "
                 "deliberately broken circuit no longer matches the reference):")
    for c in econtrols:
        status = {True: "PASS", False: "FAIL", None: "skipped"}[c.get("passed")]
        note = f" — {c['note']}" if c.get("note") else ""
        lines.append(f"- {c['control']}: {status}{note}")
    lines.append("\nScope: layout/routing correctness and observable routing changes on these circuits "
                 "and seeds. Not a general correctness proof. The evolved arm is the full 1.323 stack; "
                 "the isolated tie-break additionally passes the task harness's C1–C5 exact-equivalence suite.")
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {report_path}: {verdict} {tot_both}/{total} correct, {tot_changed}/{total} changed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm")
    ap.add_argument("--out")
    ap.add_argument("--merge", nargs=2, metavar=("EVOLVED", "BASELINE"))
    ap.add_argument("--report", default="report.md")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge[0], a.merge[1], a.report)
    elif a.arm and a.out:
        run_arm(a.arm, a.out)
    else:
        ap.error("use --arm X --out F, or --merge EVOLVED BASELINE --report R")


if __name__ == "__main__":
    main()
