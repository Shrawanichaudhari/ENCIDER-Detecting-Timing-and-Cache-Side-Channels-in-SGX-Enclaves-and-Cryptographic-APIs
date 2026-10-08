#!/usr/bin/env python3
"""Ablation: does tuning RiskSearcher's eta (random-mix share) or wD (depth
weight) close the gap to random-state seen in run_experiment.py's base
run? Real klee runs, same budget/seeds/benchmark as run_experiment.py."""
import subprocess, os, glob, statistics, json
from run_experiment import run_klee, score_run, BUDGET, SEEDS, OUTROOT, KLEE, BC

CONFIGS = [
    ("riskguided_eta0.3", ["--risk-eta=0.3"]),
    ("riskguided_eta0.5", ["--risk-eta=0.5"]),
    ("riskguided_wd0", ["--risk-wd=0.0"]),
    ("riskguided_wd0_eta0.3", ["--risk-wd=0.0", "--risk-eta=0.3"]),
]


def run_klee_extra(seed, tag, extra_args):
    outdir = os.path.join(OUTROOT, tag)
    if os.path.exists(outdir):
        subprocess.run(["rm", "-rf", outdir])
    cmd = [KLEE, "--search=riskguided", f"--max-instructions={BUDGET}",
           f"--rng-initial-seed={seed}", "--write-paths",
           f"--output-dir={outdir}"] + extra_args + [BC]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return outdir


def main():
    summary = {}
    for name, extra in CONFIGS:
        closed = []
        for sd in SEEDS:
            tag = f"{name}_seed{sd}"
            outdir = run_klee_extra(sd, tag, extra)
            sc = score_run(outdir)
            closed.append(sc["closed_nodes"])
        summary[name] = dict(n=len(closed), mean_closed_nodes=statistics.mean(closed),
                             stdev_closed_nodes=statistics.stdev(closed) if len(closed) > 1 else 0.0)
    print(f"{'config':24s} {'n':>3s} {'mean closed nodes':>18s} {'stdev':>8s}")
    for name, s in summary.items():
        print(f"{name:24s} {s['n']:3d} {s['mean_closed_nodes']:18.2f} {s['stdev_closed_nodes']:8.2f}")
    with open("/home/claude/real_eval/results_ablation.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
