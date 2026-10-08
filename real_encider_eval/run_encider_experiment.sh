#!/usr/bin/env bash
# ==============================================================================
# ENCIDER Path Scheduling Experiment Runner: test1 Benchmark
#
# Compares:
#   1. ENCIDER Default: Interleaved random-path + nurs:covnew (no -search flag)
#   2. nurs:senscov: ENCIDER's undocumented secret-aware baseline
#   3. riskguided: Ported RiskSearcher (open-comparison + secret-bonus + eta)
#   4. riskguided ablations: eta in {0.3, 0.5, 1.0} to test exploration diversity
#   5. Traditional baselines: dfs, random-path, random-state
#
# Target Benchmark: test1 (Yavuz et al., Figs. 4-5 running example)
# ==============================================================================

set -euo pipefail

ENCIDER=${ENCIDER:-/opt/encider_build/bin/klee}
BENCHMARK_DIR=${1:-/opt/ENCIDER/test/test1}
MAX_TIME_SEC=${2:-300}
OUT_DIR="results/real_encider_test1_$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$ENCIDER" ]; then
    echo "ERROR: ENCIDER binary not found at $ENCIDER"
    echo "Please build the toolchain first using baseline/Dockerfile and apply real_encider_eval/encider_riskguided.patch"
    exit 1
fi

if [ ! -d "$BENCHMARK_DIR" ]; then
    echo "ERROR: Benchmark directory not found at $BENCHMARK_DIR"
    exit 1
fi

mkdir -p "$OUT_DIR"
echo "=== Starting ENCIDER Scheduling Evaluation ==="
echo "Timestamp: $(date -u)"
echo "ENCIDER Binary: $ENCIDER"
echo "Benchmark: $BENCHMARK_DIR"
echo "Max Time per Run: ${MAX_TIME_SEC}s"
echo "Output Directory: $OUT_DIR"
echo "=============================================="

# Define search configurations
declare -A CONFIGS
CONFIGS["default"]=""
CONFIGS["nurs_senscov"]="-search=nurs:senscov"
CONFIGS["dfs"]="-search=dfs"
CONFIGS["random_path"]="-search=random-path"
CONFIGS["random_state"]="-search=random-state"
CONFIGS["riskguided_eta01"]="-search=riskguided -risk-wp=2.0 -risk-wd=0.1 -risk-ws=5.0 -risk-eta=0.1"
CONFIGS["riskguided_eta03"]="-search=riskguided -risk-wp=2.0 -risk-wd=0.1 -risk-ws=5.0 -risk-eta=0.3"
CONFIGS["riskguided_eta05"]="-search=riskguided -risk-wp=2.0 -risk-wd=0.1 -risk-ws=5.0 -risk-eta=0.5"
CONFIGS["riskguided_eta10"]="-search=riskguided -risk-wp=2.0 -risk-wd=0.1 -risk-ws=5.0 -risk-eta=1.0"

for NAME in "${!CONFIGS[@]}"; do
    RUN_DIR="$OUT_DIR/$NAME"
    mkdir -p "$RUN_DIR"
    cp "$BENCHMARK_DIR"/test1.bc "$BENCHMARK_DIR"/sensargs.txt "$RUN_DIR"/
    
    SEARCH_FLAGS=${CONFIGS[$NAME]}
    echo "[*] Running searcher: $NAME (Flags: $SEARCH_FLAGS)..."
    
    cd "$RUN_DIR"
    # Execute ENCIDER with resource monitoring
    /usr/bin/time -v "$ENCIDER" \
        $SEARCH_FLAGS \
        -max-time="$MAX_TIME_SEC" \
        -entry-point=foo \
        -lazy-init=true \
        -sensitive-inputs=sensargs.txt \
        -solver-backend=z3 \
        test1.bc > stdout.txt 2> stderr.txt || echo "[$NAME] Process exited with non-zero code: $?" | tee -a "$OUT_DIR/run_errors.txt"
    cd - > /dev/null

    # Collect telemetry if generated
    if [ -f "$RUN_DIR/secretDependentBranch_time.txt" ]; then
        echo "    Found secret-dependent branches in $NAME"
    fi
    if [ -f "$RUN_DIR/timingSideChannels_time.txt" ]; then
        echo "    Found timing side channels in $NAME"
    fi
    echo "[+] Completed: $NAME"
done

echo ""
echo "=== Summary of Reported Side Channels ==="
for NAME in "${!CONFIGS[@]}"; do
    RUN_DIR="$OUT_DIR/$NAME"
    echo "--- Searcher: $NAME ---"
    if [ -f "$RUN_DIR/secretDependentBranch_time.txt" ]; then
        echo "  Secret branches logged: $(grep -c 'Location:' "$RUN_DIR/secretDependentBranch_time.txt" || true)"
        grep -E "Time=|Location:" "$RUN_DIR/secretDependentBranch_time.txt" || true
    else
        echo "  No secretDependentBranch_time.txt produced."
    fi
    if [ -f "$RUN_DIR/timingSideChannels_time.txt" ]; then
        echo "  Timing leaks logged: $(grep -c 'Location:' "$RUN_DIR/timingSideChannels_time.txt" || true)"
        grep -E "Time=|resource ranges:|Location:" "$RUN_DIR/timingSideChannels_time.txt" || true
    else
        echo "  No timingSideChannels_time.txt produced."
    fi
    echo ""
done

echo "Evaluation complete. All raw files saved to: $OUT_DIR"
