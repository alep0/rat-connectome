#!/usr/bin/env bash
# =============================================================================
# run_statistics_analysis.sh
# =============================================================================
# Run group-level structural connectivity statistical analysis.
#
# Usage:
#   chmod +x scripts/run_statistics_analysis.sh
#   ./scripts/run_statistics_analysis.sh <root_path>
#
# The script iterates over the five connectivity variables (w, d, v, tau, fa)
# and produces comparison figures + statistical summaries for the two groups.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
if [ "$#" -lt 1 ]; then
    echo "[ERROR] Usage: $0 <root_path>"
    exit 1
fi

ROOT_PATH="$1"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR="${ROOT_PATH}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/statistics_analysis_${TIMESTAMP}.log"

log() {
    local level="$1"; shift
    echo "$(date +'%Y-%m-%d %H:%M:%S') [${level}] run_statistics_analysis.sh: $*" | tee -a "${LOG_FILE}"
}

# ---------------------------------------------------------------------------
# Validate root
# ---------------------------------------------------------------------------
if [ ! -d "${ROOT_PATH}" ]; then
    log ERROR "Root path does not exist: ${ROOT_PATH}"
    exit 1
fi

log INFO "=== Statistics analysis started ==="
log INFO "Root: ${ROOT_PATH}"

# ---------------------------------------------------------------------------
# Python invocation
# ---------------------------------------------------------------------------
python3 - <<PYEOF 2>&1 | tee -a "${LOG_FILE}"
import sys
sys.path.insert(0, '${ROOT_PATH}/source')
from logging_config import setup_logging
setup_logging('${LOG_DIR}', 'DEBUG', 'statistics_analysis')
from structural_connectivity_analysis import run_group_analysis

# variable: (output_name, color_limit, log_scale, scale_factor)
analyses = [
    ("w",   "w_structural_group_mask",   8000.0, 0, 1.0),
    ("d",   "d_structural_group_mask",      2.0, 0, 100.0),
    ("v",   "v_structural_group_mask",     20.0, 0, 1.0),
    ("tau", "tau_structural_group_mask",   10.0, 0, 1000.0),
    ("fa",  "fa_structural_group_mask",     2.0, 0, 1.0),
]

for var, out_name, clim, log_sc, fac in analyses:
    run_group_analysis(
        root='${ROOT_PATH}',
        output_name=out_name,
        model_name_1='filter_kick_out',
        group_name_1='t1',
        model_name_2='filter_kick_out',
        group_name_2='t2',
        variable=var,
        color_limit=clim,
        log_scale=log_sc,
        scale_factor=fac,
    )

print("All analyses complete.")
PYEOF

EXIT_CODE="${PIPESTATUS[0]}"
if [ "${EXIT_CODE}" -ne 0 ]; then
    log ERROR "Statistics analysis exited with code ${EXIT_CODE}."
    exit "${EXIT_CODE}"
fi

log INFO "=== Statistics analysis complete ==="
exit 0
