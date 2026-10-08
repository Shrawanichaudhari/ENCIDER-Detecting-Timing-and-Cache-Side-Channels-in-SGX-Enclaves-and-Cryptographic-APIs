# Porting RiskSearcher to ENCIDER (KLEE 1.4.0)

## 1. Context and Motivation

The paper draft proposes a risk-guided path scheduler (`RiskSelect` / `RiskSearcher`) designed to prioritize symbolic execution paths that are most likely to uncover timing and cache side channels in Intel SGX enclaves and cryptographic APIs.

In modern KLEE (upstream LLVM 15), a preliminary prototype was patched into `ExecutionTree.h` and evaluated in `real_klee_eval/`. However, that prototype had two major divergences from ENCIDER:
1. **API Divergence:** Modern KLEE uses an `ExecutionTree` / `ExecutionTreeNode` abstraction with persistent node pointers and hash sets (`std::unordered_set<ExecutionTreeNode*> closedSubtrees`).
2. **Missing Secret Guidance:** In upstream KLEE, there is no Information Flow Tracking (IFT) engine. The secret-labeling term $g(\cdot)$ had to be omitted, forcing the scheduler to evaluate all branches identically.

ENCIDER (Yavuz et al., IEEE TDSC 2023) is built on an older fork: **KLEE 1.4.0**, compiled with **LLVM/Clang 3.8** and **STP/Z3 >= 4.4**. To conduct the true evaluation promised in Section VIII-C of the paper, `RiskSearcher` had to be ported directly to ENCIDER's internal data structures and integrated with its native taint tracking engine.

---

## 2. Structural Differences: `ExecutionTree` vs. `PTree`

### Modern KLEE (LLVM 15)
- Header: `lib/Core/ExecutionTree.h`
- Node structure: `ExecutionTreeNode` with persistent `parent`, `left`, `right` pointers.
- Closed subtree tracking: Subtree closure was tracked using an external `std::unordered_set<ExecutionTreeNode*> closedSubtrees`.

### ENCIDER / KLEE 1.4.0 (LLVM 3.8)
- Header: `lib/Core/PTree.h`, Implementation: `lib/Core/PTree.cpp`
- Node structure:
  ```cpp
  struct PTreeNode {
    PTreeNode *parent, *left, *right;
    ExecutionState *data;
    ref<Expr> condition;
    bool closed; // Added by SYSREL/RiskSearcher extension
  };
  ```
- **Dynamic Leaf Pruning (`PTree::remove`):**
  In KLEE 1.4.0, when an `ExecutionState` terminates, KLEE invokes `PTree::remove(PTree::Node *n)`:
  ```cpp
  void PTree::remove(Node *n) {
    assert(!n->left && !n->right);
    do {
      Node *p = n->parent;
      if (p) {
        if (n == p->left) {
          p->left = 0;
        } else {
          assert(n == p->right);
          p->right = 0;
        }
      }
      delete n;
      n = p;
    } while (n && !n->left && !n->right);
  }
  ```
  **Consequence for Open-Comparison Calculation:**
  When one branch of a fork terminates, its leaf node is pruned, and the parent's corresponding child pointer (`left` or `right`) is set to `0` (`NULL`). The parent node itself remains alive as long as the sibling branch is still active (since `!(p->left == 0 && p->right == 0)`).
  
  Therefore, when a surviving state inspects its ancestors:
  ```cpp
  PTreeNode *parent = node->parent;
  PTreeNode *sibling = (parent->left == node) ? parent->right : parent->left;
  ```
  If the sibling has already terminated and been pruned, `sibling` will be `NULL`.
  If the sibling subtree is partially explored and marked closed, `sibling->closed` will be `true`.
  
  Thus, the sibling-closed condition in KLEE 1.4.0 is cleanly expressed as:
  ```cpp
  bool siblingClosed = (!sibling) || sibling->closed;
  ```
  If `siblingClosed && !node->closed`, exploring the current state will "close" the pair at this ancestor fork, directly fulfilling ENCIDER's dual-path completion requirement.

---

## 3. Integrating ENCIDER's Native Secret-Relevance Engine ($g(\cdot)$)

In `real_klee_eval/`, a key limitation was:
> *"This result has no secret-labeling term ($g(\cdot)$): every branch in `leaky_chain.c` is 'equally secret', so the scheduler can't yet distinguish a genuinely sensitive branch from a decoy one."*

In ENCIDER, secret tracking is a first-class citizen:
- `ExecutionState::isSecretDescendant()` returns `true` if an execution path has branched on or been influenced by a high-security input designated in `sensargs.txt`.
- ENCIDER's undocumented baseline `nurs:senscov` (`Searcher.cpp:204-208`) used this as a binary filter (weight 100 if secret descendant, 0 otherwise).

In our ported `RiskSearcher`, we connect this directly into the priority formula:
$$\text{Score}(s) = w_P \cdot P(s) + w_D \cdot D(s) + w_S \cdot g(s)$$
Where:
- $P(s)$ is the number of open ancestor comparisons this state can complete:
  $$\sum_{\text{ancestor } a} \mathbf{1}[\text{sibling}(a) \text{ is closed and } \text{branch}(a) \text{ is open}]$$
- $D(s)$ is tree depth (tie-breaker, default weight 0.1).
- $g(s)$ is `es->isSecretDescendant() ? wS : 0.0` (default $w_S = 5.0$).
- With probability $\eta$ (default 0.1, configurable via `-risk-eta`), the searcher samples uniformly at random to preserve exploration diversity and prevent greedy search collapse.

---

## 4. Implementation Details in ENCIDER Source

The port consists of modifications across 5 core files:

1. **`klee/lib/Core/PTree.h`**:
   - Added `bool closed;` member to `PTreeNode`.
2. **`klee/lib/Core/PTree.cpp`**:
   - Initialized `closed(false)` in `PTreeNode::PTreeNode` constructor.
3. **`klee/lib/Core/Searcher.h`**:
   - Added `RiskGuided` to `enum CoreSearchType`.
   - Declared `class RiskSearcher : public Searcher` with state frontier, weight parameters (`wP`, `wD`, `wS`, `eta`), `score()`, and `markClosed()`.
4. **`klee/lib/Core/Searcher.cpp`**:
   - Implemented `RiskSearcher::markClosed(ExecutionState *es)`: propagates `closed = true` up the ancestor chain.
   - Implemented `RiskSearcher::score(ExecutionState *es)`: traverses `es->ptreeNode` ancestors, counts open comparisons (`siblingClosed && !node->closed`), adds tree depth, and adds $w_S$ if `es->isSecretDescendant()`.
   - Implemented `RiskSearcher::selectState()`: with probability $\eta$ picks a random state; otherwise performs $\arg\max_{s} \text{score}(s)$.
   - Implemented `RiskSearcher::update()`: updates frontier vectors on state additions and removals.
5. **`klee/lib/Core/UserSearcher.cpp`**:
   - Registered `clEnumValN(Searcher::RiskGuided, "riskguided", "use Risk-Guided Open-Comparison Path Scheduling")`.
   - Exposed CLI options:
     - `-risk-wp=<double>`: weight per open ancestor comparison (default: 2.0).
     - `-risk-wd=<double>`: weight per tree depth (default: 0.1).
     - `-risk-ws=<double>`: weight bonus for secret-dependent branch (default: 5.0).
     - `-risk-eta=<double>`: probability of uniform-random pick for exploration diversity (default: 0.1).
   - Instantiated `new RiskSearcher(RiskWP, RiskWD, RiskWS, RiskEta)` inside `getNewSearcher()`.

---

## 5. Artifact

The complete, unified diff is exported in:
[`real_encider_eval/encider_riskguided.patch`](file:///d:/Research_Paper/encider-research/real_encider_eval/encider_riskguided.patch)
Applying this patch to a clean clone of `https://github.com/sysrel/ENCIDER` (commit `2e5408387fa48923128bae73529401ff34e70937`) integrates the scheduler seamlessly.
