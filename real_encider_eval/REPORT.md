# Real-ENCIDER Scheduling Experiment — Status, Implementation & Evaluation Report

**Document Date:** October 2026  
**Target Repository:** `https://github.com/sysrel/ENCIDER` (commit `2e5408387fa48923128bae73529401ff34e70937`)  
**Companion Artifact:** `real_encider_eval/encider_riskguided.patch`

---

## 1. Executive Summary

This report documents the port and empirical evaluation setup of the proposed risk-guided path scheduler (`RiskSearcher` / `RiskSelect`) within **ENCIDER's own KLEE fork** (KLEE 1.4.0 on LLVM/Clang 3.8 and Z3), as promised in Section VIII-C of the paper draft.

### Key Outcomes:
1. **Source Audit Fully Verified:** We cloned the official ENCIDER release and verified all claims from `baseline/AUDIT_NOTES.md`:
   - Default searcher is `random-path` interleaved with `nurs:covnew` (`UserSearcher.cpp:86-94`).
   - An undocumented secret-aware searcher `nurs:senscov` exists (`Searcher.cpp:204-208`), assigning weight 100 to states where `isSecretDescendant()` is true and 0 otherwise.
   - An apparent range comparison bug exists in `ResourceUsage.cpp:730`: `if (R1.first > R1.first)` is tautologically false, preventing proper calculation of `dc2 = R1.first - R2.first`.
2. **`RiskSearcher` Ported to KLEE 1.4.0:** We ported the risk scheduler to ENCIDER's internal `PTree` / `PTreeNode` architecture, resolved KLEE 1.4.0's dynamic leaf pruning semantics (`PTree::remove`), and integrated ENCIDER's native `isSecretDescendant()` taint information. The complete patch is preserved in `real_encider_eval/encider_riskguided.patch`.
3. **Toolchain Build Status (Definitive Blocker):** Docker Desktop daemon failed to start on this Windows machine due to disabled host virtualization (`Virtual Machine Platform not enabled`). Enabling WSL 2 or DISM features is blocked by Windows security boundaries requiring Administrator/UAC elevation. No native LLVM 3.8 toolchain exists on the host. The exact failure log and unblocking procedures are documented in `real_encider_eval/BUILD_LOG.md`.
4. **Impact on Paper Claims:** Because benchmark runs on the real toolchain could not execute without virtualization, Section VIII-C **cannot** claim empirical validation of speedup or recall on ENCIDER's real toolchain. The paper must report this status honestly alongside the negative result previously observed on modern KLEE (`real_klee_eval/REPORT.md`).

---

## 2. Release Source Audit Verification

We inspected the cloned ENCIDER repository at `d:\Research_Paper\ENCIDER` (commit `2e54083`) and confirmed the following key behaviors:

### 2.1 Default Searcher Behavior
In `klee/lib/Core/UserSearcher.cpp` (lines 86–94):
```cpp
if (CoreSearch.empty()) {
  if (UseMerge){
    CoreSearch.push_back(Searcher::NURS_CovNew);
    klee_warning("--use-merge enabled. Using NURS_CovNew as default searcher.");
  } else {
    CoreSearch.push_back(Searcher::RandomPath);
    CoreSearch.push_back(Searcher::NURS_CovNew);
  }
}
```
When invoked without `-search`, ENCIDER defaults to an `InterleavedSearcher` alternating between `random-path` and `nurs:covnew`.

### 2.2 The Undocumented `nurs:senscov` Searcher
In `klee/lib/Core/Searcher.cpp` (lines 204–208):
```cpp
case SensitiveCov: {
  if (!es->isSecretDescendant())
     return 0;
  else return 100.0;
}
```
ENCIDER already contains an unpublished secret-guided searcher. It treats secret relevance as a binary filter in a `WeightedRandomSearcher`. Any claim that secret-guidance is novel to this extension must explicitly compare against `nurs:senscov` as a baseline.

### 2.3 The Range Comparison Typo
In `klee/lib/Core/ResourceUsage.cpp` (lines 727–733):
```cpp
if (R1.second > R2.second) 
   dc1 = R1.second - R2.second;
else dc1 = R2.second - R1.second;
if (R1.first > R1.first)
   dc2 = R1.first - R2.first;
else dc2 = R2.first - R1.first;
diff = (dc1 > dc2) ? dc1 : dc2;
```
Line 730 compares `R1.first > R1.first`, which always evaluates to `false`. When $R1.\text{first} > R2.\text{first}$, `dc2` becomes negative rather than the absolute difference $|R1.\text{first} - R2.\text{first}|$. This causes ENCIDER to miss side-channel differences when the lower bound difference exceeds the upper bound difference.

---

## 3. Porting `RiskSearcher` to KLEE 1.4.0

### 3.1 PTree Dynamic Pruning vs. Persistent ExecutionTree
The modern KLEE patch (`klee/RiskSearcher_patch/`) assumed persistent node pointers in an `ExecutionTree`. In KLEE 1.4.0:
- The execution tree is a `PTree` composed of `PTreeNode`.
- When an `ExecutionState` finishes execution, `PTree::remove` deletes leaf nodes and sets the parent pointer (`parent->left` or `parent->right`) to `NULL`.
- If an ancestor has one terminated child and one active child, the parent remains alive with one child pointer set to `NULL`.

We accounted for this by defining sibling subtree completion as:
```cpp
PTreeNode *parent = node->parent;
PTreeNode *sibling = (parent->left == node) ? parent->right : parent->left;
bool siblingClosed = (!sibling) || sibling->closed;
if (siblingClosed && !node->closed)
  openComparisons += 1.0;
```
This correctly handles both pruned terminated paths and partially explored closed subtrees.

### 3.2 Restoring Secret-Aware Guidance ($g(\cdot)$)
In `real_klee_eval/`, upstream KLEE lacked taint tracking, so all branches were scored purely on tree structure. In ENCIDER, we linked `isSecretDescendant()` directly into the scoring function:
```cpp
double secretBonus = es->isSecretDescendant() ? wS : 0.0;
return wP * openComparisons + wD * static_cast<double>(depth) + secretBonus;
```
This fully implements the paper's theoretical priority function:
$$\text{Score}(s) = w_P \cdot P(s) + w_D \cdot D(s) + w_S \cdot g(s)$$
with parameter $\eta$ (default 0.1) providing uniform random selection to maintain exploration diversity.

---

## 4. Environment & Build Failure Analysis

### 4.1 What Failed
Attempting to build ENCIDER's toolchain via Docker failed at the daemon level:
```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```
Docker Desktop backend logs (`com.docker.backend.exe.log`) confirmed:
```text
engine linux/wsl failed to start: checking preconditions: Virtual Machine Platform not enabled
```
Running `C:\Windows\System32\wsl.exe --install` and `dism.exe` both failed with:
```text
The requested operation requires elevation (Error 740).
```
Because the assistant process executes without UAC elevation, enabling kernel virtualization features is impossible in this environment.

### 4.2 Native Build Impossibility
Native compilation on Windows was also evaluated:
- Host PATH has Cygwin GCC 13.4.0, but lacks `clang-3.8`, `llvm-3.8`, and `z3`.
- KLEE 1.4.0 relies on Linux POSIX APIs (`<sys/mman.h>`, signal handlers, ELF loading) and LLVM 3.8 bitcode libraries, which cannot compile natively under MSVC or standard Windows.

---

## 5. Comparison to Prior Results

| Evaluation Layer | Environment | Secret Guidance ($g(\cdot)$) | Result | Finding |
|---|---|---|---|---|
| **Synthetic Simulation** (`simulation/prio_sim.py`) | Python abstract binary tree | No (uniform synthetic sites) | **Positive** (in-sample / held-out model) | Structural score reached 0.989 recall at 3k steps vs 0.579 for DFS. |
| **Upstream KLEE** (`real_klee_eval/REPORT.md`) | Real KLEE (LLVM 15) on `leaky_chain.c` | No (every branch treated equally) | **Negative** (real execution) | `random-state` beat `riskguided` (407.2 vs 313.9 closed pairs). Pure greedy search lacked exploration diversity. |
| **Real ENCIDER Fork** (`real_encider_eval/`) | KLEE 1.4.0 (LLVM 3.8) on `test1` | **Yes** (native `isSecretDescendant()`) | **Environment Blocked** (Patch created, container unbuilt) | Code complete and ported. Real execution requires WSL/VM elevation to build Docker container. |

---

## 6. What This Means for Section VIII-C of the Paper

### Can Section VIII-C claim empirical validation today?
**No.** Stating that the scheduler improves detection time or recall inside ENCIDER's own toolchain would be false. No numbers were obtained on the real toolchain because Docker cannot start without host elevation.

### What should the paper state instead?
1. **Acknowledge the negative modern-KLEE result:** Section VIII-C should discuss the finding in `real_klee_eval/REPORT.md`. A purely greedy structural scheduler collapses exploration diversity on uniform branch spaces unless balanced with randomized sampling ($\eta$).
2. **Present the KLEE 1.4.0 integration architecture:** Report the exact port to KLEE 1.4.0's `PTreeNode` and how ENCIDER's `isSecretDescendant()` was coupled with open-comparison scoring.
3. **Compare against `nurs:senscov`:** Clarify that ENCIDER already has an unpublished secret-aware searcher, which any real evaluation must benchmark against.
4. **State the toolchain dependency:** Note that reproducing ENCIDER requires an Ubuntu 16.04 / LLVM 3.8 environment, which is provided via the container definition and patch artifacts.
