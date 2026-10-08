#!/usr/bin/env python3
"""
REAL KLEE experiment (not a simulation): runs klee's real dfs, random-state
and our new riskguided searcher (lib/Core/Searcher.cpp::RiskSearcher, linked
into a real, compiled klee binary) on leaky_chain.bc, a fixed instruction
budget each, multiple seeds for the randomized searchers, and measures how
many ExecutionTree branch-pair "comparisons" each run closes (both sides
terminated) within budget, by reading KLEE's own --write-paths .path files.
This mirrors the metric used in the paper's synthetic simulation
(sim/prio_sim.py's "detected / total" recall@budget) but computed from a
real, running dynamic-symbolic-execution tool instead of an abstract model.
"""
import subprocess, os, glob, statistics, json, sys

KLEE = "/home/claude/klee-upstream/build/bin/klee"
BC = "/home/claude/real_eval/leaky_chain.bc"
BUDGET = 20000          # --max-instructions
SEEDS = list(range(1, 21))   # 20 seeds for the randomized searchers
OUTROOT = "/home/claude/real_eval/runs"

os.makedirs(OUTROOT, exist_ok=True)


def run_klee(searcher, seed, tag):
    outdir = os.path.join(OUTROOT, tag)
    if os.path.exists(outdir):
        subprocess.run(["rm", "-rf", outdir])
    cmd = [KLEE, f"--search={searcher}", f"--max-instructions={BUDGET}",
           f"--rng-initial-seed={seed}", "--write-paths",
           f"--output-dir={outdir}", BC]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    stats = {"completed": None, "partial": None, "tests": None}
    for line in r.stdout.splitlines() + r.stderr.splitlines():
        if "completed paths =" in line:
            stats["completed"] = int(line.strip().split("=")[-1])
        elif "partially completed paths =" in line:
            stats["partial"] = int(line.strip().split("=")[-1])
        elif "generated tests =" in line:
            stats["tests"] = int(line.strip().split("=")[-1])
    return outdir, stats


def score_run(outdir):
    """Read every .path file (one 0/1 per fork, in order) and count how
    many ancestor prefixes got BOTH children terminated within budget."""
    paths = []
    for p in sorted(glob.glob(os.path.join(outdir, "*.path"))):
        with open(p) as f:
            seq = tuple(int(x) for x in f.read().split())
        paths.append(seq)

    has_child = {}  # prefix(tuple) -> set of {0,1} children seen
    for seq in paths:
        for d in range(len(seq)):
            prefix = seq[:d]
            bit = seq[d]
            has_child.setdefault(prefix, set()).add(bit)

    closed = sum(1 for kids in has_child.values() if kids == {0, 1})
    total_nodes = len(has_child)
    return dict(num_paths=len(paths), closed_nodes=closed,
                total_internal_nodes=total_nodes,
                recall=closed / total_nodes if total_nodes else 0.0)


def main():
    results = {}

    # DFS: fully deterministic, no seed dependence -> one run
    outdir, stats = run_klee("dfs", 1, "dfs_seed1")
    sc = score_run(outdir)
    results["dfs"] = {"runs": [dict(seed=1, **stats, **sc)]}

    for name in ["random-state", "riskguided"]:
        runs = []
        for sd in SEEDS:
            tag = f"{name.replace(':', '_')}_seed{sd}"
            outdir, stats = run_klee(name, sd, tag)
            sc = score_run(outdir)
            runs.append(dict(seed=sd, **stats, **sc))
        results[name] = {"runs": runs}

    # Summary
    summary = {}
    for name, d in results.items():
        closed = [r["closed_nodes"] for r in d["runs"]]
        recall = [r["recall"] for r in d["runs"]]
        npaths = [r["num_paths"] for r in d["runs"]]
        summary[name] = dict(
            n=len(closed),
            mean_closed_nodes=statistics.mean(closed),
            stdev_closed_nodes=statistics.stdev(closed) if len(closed) > 1 else 0.0,
            mean_recall=statistics.mean(recall),
            mean_num_paths=statistics.mean(npaths),
        )

    out = {"budget_instructions": BUDGET, "seeds": SEEDS, "results": results,
           "summary": summary}
    with open("/home/claude/real_eval/results_real_klee.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"{'searcher':14s} {'n':>3s} {'mean closed nodes':>18s} {'stdev':>8s} {'mean recall':>12s} {'mean #paths':>12s}")
    for name, s in summary.items():
        print(f"{name:14s} {s['n']:3d} {s['mean_closed_nodes']:18.2f} "
              f"{s['stdev_closed_nodes']:8.2f} {s['mean_recall']:12.4f} {s['mean_num_paths']:12.1f}")


if __name__ == "__main__":
    main()
