import prio_sim as p, random, statistics, time, json, sys
D, P_H, Q, BASE, B = 20, 0.4, 0.5, 0.2, 3000
W2 = (0.0, 10.0, 10.0, 0.1)
rho, s = float(sys.argv[1]), sys.argv[2]
def boot(xs, n=2000, seed=1):
    r = random.Random(seed); m = []
    for _ in range(n):
        smp = [xs[r.randrange(len(xs))] for _ in xs]; m.append(sum(smp)/len(smp))
    m.sort(); return m[int(0.025*n)], m[int(0.975*n)]
res, t0 = [], time.perf_counter()
for sd in range(60):
    prog = p.make_program(50000 + sd, D, P_H, Q, BASE, rho)
    if sum(prog[1]) == 0: continue
    res.append(p.run(prog, D, s, B, 9000 + sd, W=W2))
dt = (time.perf_counter() - t0) / len(res)
rec = [x['detected']/x['total'] for x in res]
ttfl = [x['first'] if x['first'] is not None else B+1 for x in res]
lo, hi = boot(rec)
curve = [statistics.mean(x['curve'][k]/x['total'] if k < len(x['curve']) else x['detected']/x['total'] for x in res) for k in range(30)]
rec_d = dict(rho=rho, sched=s, n=len(res), recall=statistics.mean(rec), ci=[lo, hi], ttfl_med=statistics.median(ttfl),
             none=sum(x['first'] is None for x in res), ms_per_run=dt*1000, curve=curve)
print(json.dumps({k: v for k, v in rec_d.items() if k != 'curve'}))
open('heldout.jsonl', 'a').write(json.dumps(rec_d) + '\n')
