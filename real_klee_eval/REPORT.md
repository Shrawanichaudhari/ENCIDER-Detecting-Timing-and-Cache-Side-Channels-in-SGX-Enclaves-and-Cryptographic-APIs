# Real-KLEE scheduling experiment — results and honest discussion

**What this is:** the first result in this project that comes from an
actual, running, compiled dynamic symbolic executor (`klee/klee` upstream
+ a new `RiskSearcher` patched directly into its C++ core — see
`../klee/RiskSearcher_patch/`), not from the Python abstraction in
`../simulation/prio_sim.py`. See `BUILD.md` for exactly what is and isn't
the same as ENCIDER's own toolchain and detection logic.

## Setup

- Benchmark: `leaky_chain.c` — `klee_make_symbolic` over a 20-byte
  buffer, one conditional branch per byte, each branch's two sides doing
  different amounts of work (a stand-in for a timing/cache side channel's
  differing resource usage). This operationalizes the same abstract
  model `prio_sim.py` uses (`D` sequential branch "sites", complete
  binary tree of depth `D`) as real LLVM IR that real KLEE forks on.
- Budget: `--max-instructions=20000` per run (small relative to the
  ~2^20-leaf tree, so scheduling order matters — with no budget, all
  three searchers eventually explore everything and "detection" is
  trivial).
- Metric: for every ancestor node in the real `ExecutionTree` KLEE built
  during the run, whether **both** children produced a terminated path
  within budget — read directly from KLEE's own `--write-paths` output.
  This is the real-KLEE analogue of the paper's "detected leaky site"
  condition (ENCIDER's own rule: a site is reported only once both sides
  of the branch have a terminated path).
- Searchers compared: KLEE's built-in `dfs` (deterministic, 1 run) and
  `random-state` (20 seeds), against the new `riskguided` (20 seeds),
  which scores each candidate state by how many ancestor branches it
  could "close" (its sibling subtree already has a terminated path) plus
  a small depth term, with probability `eta` of a uniform-random pick
  instead (default `eta=0.1`) — the real implementation of the paper's
  Eq. (7)-(8) structural score, minus the secret-labeling term `g(·)`
  (see `BUILD.md` for why).

## Headline result (default `riskguided`, `eta=0.1`)

| searcher       | seeds | mean closed-node pairs | stdev | mean recall | mean #paths |
|----------------|------:|------------------------:|------:|------------:|------------:|
| dfs            |     1 |                   293.0 |  0.00 |      0.1485 |       294.0 |
| random-state   |    20 |                   407.2 |  3.18 |      0.2117 |       408.1 |
| **riskguided** |    20 |               **313.9** |  1.74 |      0.1596 |       314.9 |

**This does not support the paper's hypothesis as stated.** On this
benchmark and budget, KLEE's own uniform `random-state` searcher closes
~30% *more* branch-pair comparisons than the structural, greedy
`riskguided` scheduler — and beats plain `dfs` too. Full numbers:
`results_real_klee.json`.

## Why, and what we checked before trusting that number

A purely greedy argmax over the structural score has no exploration
diversity: once it starts preferring states that look locally promising,
it tends to keep deepening the same few branches rather than sampling
broadly, and on an i.i.d. branch-chain benchmark (no real asymmetry
between "interesting" and "uninteresting" subtrees beyond the score
itself) broad sampling matters more than greedy local preference. Two
checks support this reading rather than a bug:

1. **Monotone improvement with more randomness** (`run_ablation.py`,
   `results_ablation.json`): raising `eta` (the random-pick share) from
   0.1 → 0.3 → 0.5 moves the mean closed-node count from 313.9 → 327.0 →
   352.6, monotonically closing the gap to `random-state`'s 407.2.
2. **`eta=1.0` recovers `random-state` almost exactly**: 406.4 ± 3.23 vs.
   `random-state`'s real 407.2 ± 3.18 — i.e. our implementation, with its
   structural term switched off, reduces to the same behavior as KLEE's
   own random-state searcher, which is what should happen and confirms
   the scoring/bookkeeping isn't just broken.

So the implementation looks correct; the structural heuristic itself, in
this pure-greedy form, is the weaker policy on this benchmark.

## What this honestly means for the paper

- The synthetic `prio_sim.py` result in the paper (structural scheduler
  beating `dfs`/`random-state` at 3,000-step budget) does not
  automatically carry over to a real symbolic executor's actual state
  space and solver-driven forking — the two environments differ in ways
  (constraint caching, state-size growth, concretization) the abstract
  model doesn't capture.
- The likely fix (diversify selection, e.g. mix with `eta` the way the
  paper's Eq. (8) always intended rather than defaulting it low, or move
  to a weighted-probability draw instead of hard argmax — closer to
  KLEE's own `WeightedRandomSearcher` pattern) is still untested here;
  `run_ablation.py` only swept `eta` and `wD`, not a weighted-sampling
  variant.
- This result has **no secret-labeling term** (`g(·)`): every branch in
  `leaky_chain.c` is "equally secret," so the scheduler can't yet
  distinguish a genuinely sensitive branch from a decoy one the way the
  paper's full design intends. That's the next real gap to close, and it
  needs ENCIDER's own IFT machinery (or a standalone approximation of
  it), not just KLEE's stock tree structure.
- Per the project's own evidence standards: this is a negative result on
  a real tool, reported as such, not smoothed over. It replaces the
  earlier "never been run" status of the KLEE-based evaluation with a
  real, if currently unfavorable, first measurement.
