"""
prio_sim.py -- SYNTHETIC scheduling simulation for risk-guided path prioritization.
This is NOT a KLEE/ENCIDER experiment and makes no claim about real programs.

Model (abstraction of an ENCIDER-style symbolic execution tree):
  * A straight-line program with D conditional branch SITES s_0..s_{D-1};
    the execution tree is the complete binary tree of depth D; every tree node at
    depth d is an instance of site s_d.  A path terminates at depth D.
  * Site s_d branches on secret (High) data w.p. P_H; an H-site is 'leaky'
    (its two sides have different resource usage) w.p. Q.
  * A leaky site is DETECTED once, for some tree node a of that site, both child
    subtrees of a contain >=1 terminated path (abstraction of the pairwise check in
    Algorithm 3 of ENCIDER; LC-compatibility is assumed).
  * Static indicator g(s): Bernoulli(BASE + rho*(1-BASE)) for leaky sites,
    Bernoulli(BASE) for others. rho=0 -> uninformative; rho=1 -> perfect.
Cost model: one step per tree-node expansion. Budget B steps.
Schedulers: DFS, BFS, RandomState, RiskStruct (H-count + open-comparison), RiskFull (+ g).
"""
import random, heapq, statistics, json
from collections import defaultdict

def make_program(seed, D, P_H, Q, BASE, rho):
    r = random.Random(seed)
    isH = [r.random() < P_H for _ in range(D)]
    leaky = [h and r.random() < Q for h in isH]
    g = [1 if r.random() < ((BASE + rho * (1 - BASE)) if lk else BASE) else 0 for lk in leaky]
    return isH, leaky, g

def run(prog, D, sched, budget, seed, W=(1.0, 2.0, 2.0, 0.1)):
    global_W = W
    isH, leaky, g = prog
    wH, wP, wG, wD = W
    r = random.Random(seed)
    total = sum(leaky)
    has_leaf = set()            # (depth, index) nodes whose subtree has a terminated path
    det_sites = set(); first = None; curve = []
    def score(node, use_g):
        d, idx = node
        s = wD * d; dd, ii = d, idx
        while dd > 0:
            pd, pi = dd - 1, ii // 2
            sib = (dd, ii ^ 1)
            if isH[pd]:
                s += wH
                if sib in has_leaf and (dd, ii) not in has_leaf:   # open comparison
                    s += wP * (1 + (wG / wP) * g[pd] if use_g else 1)
            dd, ii = pd, pi
        return s
    use_g = sched == 'risk_full'
    frontier = [(0, 0)]; heap = [(-score((0, 0), use_g), r.random(), (0, 0))]
    steps = 0
    while steps < budget:
        if sched.startswith('risk'):
            if not heap: break
            while True:
                negs, _, node = heapq.heappop(heap)
                cur = score(node, use_g)
                if abs(cur + negs) < 1e-9 or not heap: break
                heapq.heappush(heap, (-cur, r.random(), node))
        else:
            if not frontier: break
            if sched == 'dfs': node = frontier.pop()
            elif sched == 'bfs': node = frontier.pop(0)
            else:
                k = r.randrange(len(frontier)); frontier[k], frontier[-1] = frontier[-1], frontier[k]
                node = frontier.pop()
        steps += 1
        d, idx = node
        if d == D:                                   # terminated path
            rescore = True
            dd, ii = d, idx
            while True:
                has_leaf.add((dd, ii))
                if dd == 0: break
                pd, pi = dd - 1, ii // 2
                if leaky[pd] and pd not in det_sites and (dd, 2*pi) in has_leaf and (dd, 2*pi+1) in has_leaf:
                    det_sites.add(pd)
                    if first is None: first = steps
                dd, ii = pd, pi
        else:
            kids = [(d + 1, 2 * idx), (d + 1, 2 * idx + 1)]
            if sched == 'dfs': r.shuffle(kids)
            if sched.startswith('risk'):
                for c in kids: heapq.heappush(heap, (-score(c, use_g), r.random(), c))
            else:
                frontier.extend(kids)
        if sched.startswith('risk') and d == D:
            heap = [(-score(n, use_g), r.random(), n) for (_, _, n) in heap]
            heapq.heapify(heap)
        if steps % 100 == 0: curve.append(len(det_sites))
    return dict(first=first, detected=len(det_sites), total=total, curve=curve)

if __name__ == '__main__':
    D, P_H, Q, BASE, BUDGET = 20, 0.4, 0.5, 0.2, 3000
    SCHEDS = ['dfs', 'bfs', 'rand_state', 'risk_struct', 'risk_full']
    RHOS = [0.0, 0.9]; SEEDS = [s for s in range(60)]
    out = {'config': dict(D=D, P_H=P_H, Q=Q, BASE=BASE, BUDGET=BUDGET, seeds=len(SEEDS))}
    for rho in RHOS:
        for s in SCHEDS:
            res = []
            for sd in SEEDS:
                prog = make_program(1000 + sd, D, P_H, Q, BASE, rho)
                if sum(prog[1]) == 0: continue
                res.append(run(prog, D, s, BUDGET, 77 + sd))
            out[f'{rho}|{s}'] = res
            rec = [x['detected'] / x['total'] for x in res]
            f = [x['first'] if x['first'] is not None else BUDGET + 1 for x in res]
            print(f"rho={rho} {s:12s} n={len(res)} recall@B mean={statistics.mean(rec):.3f} "
                  f"median TTFL={statistics.median(f):6.0f} none={sum(x['first'] is None for x in res)}")
    json.dump(out, open('results.json', 'w'))

def sweep(W, label, rhos=(0.0, 0.9), budget=3000):
    D, P_H, Q, BASE = 20, 0.4, 0.5, 0.2
    res_all = {}
    for rho in rhos:
        for s in ['dfs', 'rand_state', 'risk_struct', 'risk_full']:
            res = []
            for sd in range(60):
                prog = make_program(1000 + sd, D, P_H, Q, BASE, rho)
                if sum(prog[1]) == 0: continue
                res.append(run(prog, D, s, budget, 77 + sd, W=W))
            res_all[f'{rho}|{s}'] = res
            rec = [x['detected'] / x['total'] for x in res]
            f = [x['first'] if x['first'] is not None else budget + 1 for x in res]
            print(f"[{label}] rho={rho} {s:12s} recall@B={statistics.mean(rec):.3f} medTTFL={statistics.median(f):6.0f}")
    return res_all
