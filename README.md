# ENCIDER risk-guided scheduling — research code

Companion code for the paper extending ENCIDER [Yavuz et al., IEEE TDSC
2023] with a risk-guided path-prioritization scheduler. **The paper
itself is not in this repo** — this holds only the research code: the
synthetic simulation, the source audit of released ENCIDER, and (new) a
real KLEE build with the proposed scheduler patched in and run.

## Status, honestly, as of this commit

| Piece | Status |
|---|---|
| Synthetic scheduling simulation (`simulation/`) | Done. Idealized abstract model, not evidence about real programs — see its own docstring. |
| Source audit of released ENCIDER (`baseline/AUDIT_NOTES.md`) | **Verified against real source clone.** Confirmed default searcher (`random-path` + `nurs:covnew`), undocumented `nurs:senscov` secret-guidance, and range comparison typo in `ResourceUsage.cpp:730`. |
| Data-cache leak check as a standalone Z3 query (`analysis/dcache_check.py`) | Done, runs. |
| Upstream KLEE implementation (`klee/RiskSearcher_patch/`) | Real patch against modern KLEE (LLVM 15). Evaluated in `real_klee_eval/REPORT.md` with an honest negative result showing pure greedy search lacks diversity. |
| ENCIDER KLEE 1.4.0 Port (`real_encider_eval/`) | **Port complete.** `RiskSearcher` ported to ENCIDER's `PTree`/`PTreeNode` structure, handles `PTree::remove` dynamic pruning, integrates native `isSecretDescendant()` taint tracking, and exposes `-search=riskguided` CLI options. Patch: `real_encider_eval/encider_riskguided.patch`. |
| ENCIDER toolchain build (`real_encider_eval/BUILD_LOG.md`) | **Blocked by host virtualization prerequisites.** Docker Desktop failed to start on Windows host (`Virtual Machine Platform not enabled`); enabling WSL2/DISM requires Administrator/UAC elevation. No native LLVM 3.8 toolchain on host. Unblocking steps documented. |
| Real ENCIDER evaluation (`real_encider_eval/REPORT.md`) | Experiment runner (`real_encider_eval/run_encider_experiment.sh`) and report ready. No fabricated numbers: execution pending toolchain container build on a virtualization-enabled host. |

## Layout

```
simulation/          synthetic scheduling simulation (prio_sim.py, heldout1.py)
results/             simulation output (heldout.jsonl)
analysis/            data-cache leak check as a Z3 query (dcache_check.py)
klee/
  RiskSearcher_patch/   real patch against klee/klee upstream (LLVM 15)
real_klee_eval/      the upstream KLEE build/run on leaky_chain.c (REPORT.md)
baseline/            ENCIDER's own Dockerfile/run script + initial audit notes
real_encider_eval/   the real ENCIDER (KLEE 1.4.0) port: patch, porting notes,
                     build logs, experiment runner, and honest report (REPORT.md)
```

## Where to start reading

1. `real_encider_eval/REPORT.md` — the newest report on extending ENCIDER's
   actual KLEE 1.4.0 fork, verifying source internals, and build blockers.
2. `real_encider_eval/PORTING_NOTES.md` — architectural details on porting
   from modern KLEE's `ExecutionTree` to KLEE 1.4.0's `PTree`, handling dynamic
   pruning, and integrating `isSecretDescendant()`.
3. `real_klee_eval/REPORT.md` — prior upstream KLEE evaluation and negative result.
4. `baseline/AUDIT_NOTES.md` — verified source audit of released ENCIDER.
5. `simulation/prio_sim.py` — original synthetic simulation model.
