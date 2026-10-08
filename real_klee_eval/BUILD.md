# Building and running this experiment from scratch

This is the exact sequence used to produce `results_real_klee.json` and
`results_ablation.json`. It builds a **real KLEE**, applies the
`RiskSearcher` patch, and runs it on a real (if synthetic-structured) C
program — this is genuine dynamic symbolic execution, not a simulation.

## 1. Why this is modern KLEE, not ENCIDER's exact toolchain

ENCIDER [Yavuz et al., TDSC 2023] is built on a fork of **KLEE 1.4.0 on
LLVM/clang 3.8** (2016-era). That toolchain is not installable here:
Docker Hub / GHCR image pulls and the old Ubuntu package archives
(`old-releases.ubuntu.com`) are both blocked by this sandbox's egress
policy, and building LLVM 3.8 from source would take several hours of
unattended compute this session doesn't have.

So this uses the **actively maintained `klee/klee` upstream** (commit
`9a36a6782b814fe1fa37439652b875114faa0e20`) on **LLVM 15**, built with
only the Z3 solver (no STP) and the POSIX/uClibc runtime disabled. That
means:

- **This is real, runs for real, and the results are real** — not a
  python abstraction of a symbolic executor.
- **This is not ENCIDER.** None of ENCIDER's own detection machinery
  (byte-level information-flow / H-L labeling, the GEP-based data-cache
  check, the pairwise `CacheDiff` batch detector) is reproduced here.
  What's tested is narrower and more honest: *does a structural,
  open-comparison-guided scheduler explore a secret-branch-shaped tree
  better than KLEE's own built-in searchers, under a fixed budget?*
  That is the scheduling question the paper's Section IV–V formalizes,
  tested on a real tool instead of `sim/prio_sim.py`'s abstract model.

## 2. Install the toolchain (Ubuntu 24.04)

```bash
sudo apt-get install -y llvm-15 llvm-15-dev llvm-15-tools clang-15 \
    libz3-dev z3 zlib1g-dev libsqlite3-dev libboost-dev \
    libboost-system-dev libboost-filesystem-dev libboost-program-options-dev \
    libcap-dev libgoogle-perftools-dev cmake ninja-build
```

## 3. Get KLEE and apply the patch

```bash
git clone https://github.com/klee/klee.git klee-upstream
cd klee-upstream
git checkout 9a36a6782b814fe1fa37439652b875114faa0e20
git apply ../klee/RiskSearcher_patch/riskguided_searcher.patch
```

## 4. Configure and build

```bash
mkdir build && cd build
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVMCC=/usr/bin/clang-15 -DLLVMCXX=/usr/bin/clang++-15 \
  -DENABLE_SOLVER_Z3=ON -DENABLE_SOLVER_STP=OFF \
  -DENABLE_POSIX_RUNTIME=OFF -DENABLE_KLEE_UCLIBC=OFF \
  -DENABLE_UNIT_TESTS=OFF -DENABLE_SYSTEM_TESTS=OFF \
  -DENABLE_TCMALLOC=OFF -DENABLE_DOCS=OFF ..
ninja
```

This produces `build/bin/klee` with a new `-search=riskguided` option
(plus `-risk-wp`, `-risk-wd`, `-risk-eta` to tune it), alongside KLEE's
normal `dfs`, `random-state`, `random-path`, `nurs:*` searchers.

## 5. Compile the test program and run the experiment

```bash
clang-15 -I klee-upstream/include -emit-llvm -c -g -O0 \
  -Xclang -disable-O0-optnone real_klee_eval/leaky_chain.c \
  -o real_klee_eval/leaky_chain.bc

cd real_klee_eval
python3 run_experiment.py   # dfs / random-state / riskguided, 20 seeds each
python3 run_ablation.py     # eta / wD sensitivity sweep
```

Each run takes well under a minute on 2 cores; the full sweep in
`run_ablation.py` takes under a minute too. See `REPORT.md` for what the
numbers actually say.
