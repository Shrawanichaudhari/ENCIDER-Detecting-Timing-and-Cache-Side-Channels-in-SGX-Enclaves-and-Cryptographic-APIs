# ENCIDER release audit (commit 2e54083, 2022-10-10) -- code reading only, nothing built

| Finding | File | Consequence |
|---|---|---|
| KLEE 1.4.0 fork, LLVM/clang 3.8, STP or Z3 >= 4.4 | klee/CMakeLists.txt, INSTALL.txt | Needs Ubuntu 16.04-era toolchain (Dockerfile here) |
| Default searcher = random-path interleaved with nurs:covnew | klee/lib/Core/UserSearcher.cpp | Baseline B0; no bundled test sets -search |
| Undocumented nurs:senscov: weight 100 for secret descendants, else 0 | klee/lib/Core/Searcher.cpp | Closest existing baseline (B5); no open-comparison term |
| onlycompletedpaths = true: report needs terminated paths on both sides | klee/lib/Core/ResourceUsage.cpp | Confirms the mechanism RISKSELECT targets |
| propagate()/checkLeakage() run once after exploration | klee/lib/Core/Executor.cpp | No discovery timestamps; needs ONTERMINATE hook |
| diff = max(dc1, dc2); guard `R1.first > R1.first` always false | klee/lib/Core/ResourceUsage.cpp (printLeakage) | Min-only differences reported in one pair order only; apparent typo, untested |
| Endpoint-difference range comparison is not monotone | same | Proposition 1 holds for pairwise rule (4), not for released batch detector under a budget |
| Benchmark sensitivity/API specs not shipped; 22 unit tests + generic models | test/, models/ | Reproducing Table XII needs reconstructed specs |
