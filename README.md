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
| Source audit of released ENCIDER (`baseline/AUDIT_NOTES.md`) | Done. Code-reading only; nothing built. |
| Data-cache leak check as a standalone Z3 query (`analysis/dcache_check.py`) | Done, runs. |
| ENCIDER's own baseline (its Dockerfile, `baseline/`) | **Still not built.** Blocked here by sandbox network policy (Docker registries + old-Ubuntu archives are both blocked) — see `real_klee_eval/BUILD.md` for the specifics and what was used instead. |
| `RiskSearcher` scheduler | **Now real.** Patched directly into real `klee/klee` upstream C++ source (`klee/RiskSearcher_patch/`), compiled, linked into a real `klee` binary, and run (`real_klee_eval/`). This replaces the earlier `STATUS: UNTESTED SKELETON` file. |
| KLEE-based evaluation | **First real run exists, and it's a negative result** — see `real_klee_eval/REPORT.md`. `random-state`, KLEE's own built-in searcher, currently beats the structural `riskguided` scheduler on the tested benchmark/budget. Ablations traced the gap to a lack of exploration diversity in the pure-greedy scoring, not an implementation bug. |
| Full ENCIDER integration (byte-level IFT, H-ancestor labeling, data-cache check, run on ENCIDER's actual benchmarks) | Not done. `real_klee_eval/` runs on vanilla upstream KLEE (LLVM 15), not ENCIDER's own fork/toolchain/detection logic — see `real_klee_eval/BUILD.md` §1 for exactly why and what the gap is. |

## Layout

```
simulation/        synthetic scheduling simulation (prio_sim.py, heldout1.py)
results/           simulation output (heldout.jsonl)
analysis/          data-cache leak check as a Z3 query (dcache_check.py)
klee/
  RiskSearcher_patch/   real patch against klee/klee upstream + scope notes
real_klee_eval/    the real KLEE build/run: benchmark, experiment scripts,
                   results, and an honest write-up (REPORT.md)
baseline/          ENCIDER's own Dockerfile/run script + the source audit
```

## Where to start reading

1. `real_klee_eval/REPORT.md` — the newest, most concrete result: what
   was actually run on real KLEE, and what it found.
2. `klee/RiskSearcher_patch/README.md` — what the new searcher does and
   does not reproduce from the paper's full design.
3. `baseline/AUDIT_NOTES.md` — what reading ENCIDER's released source
   actually turned up (its default searcher, an undocumented
   `nurs:senscov`, a range-comparison that looks like a bug).
4. `simulation/prio_sim.py` — the original synthetic model this project
   started from; still useful as a cheap sanity check, but its docstring
   says plainly it's not evidence about real enclaves or libraries.
