# RiskSearcher — real KLEE integration

`riskguided_searcher.patch` is a real `git diff` against
[`klee/klee`](https://github.com/klee/klee) commit
`9a36a6782b814fe1fa37439652b875114faa0e20`, adding a new
`RiskSearcher` class (in `lib/Core/Searcher.h` / `lib/Core/Searcher.cpp`)
and wiring it into `lib/Core/UserSearcher.cpp` as `-search=riskguided`,
with `-risk-wp` / `-risk-wd` / `-risk-eta` to tune its three weights.

**This supersedes the old `klee/RiskSearcher.h` skeleton** that shipped
in the first version of this repo, which was explicitly marked
`STATUS: UNTESTED SKELETON` and had never been compiled. This patch
*has* been compiled, linked into a real `klee` binary, and run — see
`../../real_klee_eval/` for the build steps and results.

## Scope, stated plainly

`RiskSearcher` scores a candidate state by how many of its ancestor
branches it could "close" (the sibling subtree already produced a
terminated path) plus a small depth term, with an `eta` chance of a
uniform-random pick for diversity. That is a real implementation of the
paper's *structural* scoring idea (Eq. 7–8, minus the static indicator
`g(·)`). It is **not** ENCIDER's own detection logic:

- No byte-level information-flow / H-L labeling — "secret" vs "public"
  branches aren't distinguished; every branch is treated as a candidate
  comparison.
- No data-cache / GEP address-mask check (Eq. 2 in the paper,
  implemented as a standalone Z3 query in `../../analysis/dcache_check.py`,
  not inside KLEE here).
- No integration with ENCIDER's own H-ancestor tracking or
  `ResourceUsage.cpp`/`CacheDiff` batch detector — this runs on vanilla
  upstream KLEE, not ENCIDER's fork.

See `../../real_klee_eval/REPORT.md` for what this actually measured
once it was run — a real, honestly-reported negative result relative to
KLEE's own `random-state` searcher at the tested budget.

To apply:
```
cd klee-upstream   # a clone of klee/klee at the commit above
git apply /path/to/riskguided_searcher.patch
```
