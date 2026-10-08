#!/usr/bin/env bash
# First baseline experiment (UNTESTED until the image builds): run ENCIDER's test1 -- the running
# example of Yavuz et al. -- under each searcher and keep every output directory.
# Usage inside the container:  ./run_test1_searchers.sh /opt/ENCIDER/test/test1 [max_time_s]
set -euo pipefail
T=${1:?path to ENCIDER/test/test1}; MAXT=${2:-300}
OUT=results/test1_$(date +%Y%m%d_%H%M%S); mkdir -p "$OUT"
# "default" = no -search flag -> random-path interleaved with nurs:covnew (UserSearcher.cpp)
for S in default dfs bfs random-state random-path nurs:covnew nurs:senscov; do
  D="$OUT/${S//:/_}"; mkdir -p "$D"; cp "$T"/test1.bc "$T"/sensargs.txt "$D"/
  FLAG=(); [ "$S" != default ] && FLAG=(-search="$S")
  ( cd "$D" && /usr/bin/time -v "$ENCIDER" "${FLAG[@]}" -max-time="$MAXT" \
      -entry-point=foo -lazy-init=true -sensitive-inputs=sensargs.txt \
      -solver-backend=z3 test1.bc ) > "$D/stdout.txt" 2> "$D/stderr.txt" || echo "run $S exited non-zero" | tee -a "$OUT/errors.txt"
  echo "$S done"
done
# Expected per [1, Figs. 4-5]: interference between ru1 and ru4 (same L, different H).
grep -l "Timing" "$OUT"/*/stderr.txt || true
