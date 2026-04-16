#!/usr/bin/env bash
# =============================================================================
# run_gaussian_fitting.sh
# =============================================================================
# Run the Gaussian tau-fitting pipeline for a single subject.
#
# Usage:
#   chmod +x scripts/run_gaussian_fitting.sh
#   ./scripts/run_gaussian_fitting.sh \
#       <root_path> <data_dir> <output_dir> <threshold> <rat_id>
#
# Arguments:
#   root_path   - Absolute path to the project root
#   data_dir    - Relative path to input dictionaries (e.g. /results/t2/FA_RN_SI_v0-1_th-0)
#   output_dir  - Relative path for outputs (e.g. /results/t2/FA_RN_SI_v0-1_th-0.0/filter_kick_out)
#   threshold   - Fibre filter threshold (e.g. 0.0)
#   rat_id      - Subject identifier (e.g. R01)
#
# Example:
#   ./scripts/run_gaussian_fitting.sh \
#       /workspace/connectome \
#       /results/t2/FA_RN_SI_v0-1_th-0 \
#       /results/t2/FA_RN_SI_v0-1_th-0.0/filter_kick_out/R01 \
#       0.0 \
#       R01 
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------
if [ "$#" -ne 5 ]; then
    echo "[ERROR] Expected 5 arguments, got $#."
    echo "Usage: $0 <root_path> <data_dir> <output_dir> <threshold> <rat_id>"
    exit 1
fi

ROOT_PATH="$1"
DATA_DIR="$2"
OUTPUT_DIR="$3"
THRESHOLD="$4"
RAT_ID="$5"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR="${ROOT_PATH}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/gaussian_fitting_${RAT_ID}_${TIMESTAMP}.log"

log() {
    local level="$1"
    shift
    local message="$*"
    echo "$(date +'%Y-%m-%d %H:%M:%S') [${level}] run_gaussian_fitting.sh: ${message}" | tee -a "${LOG_FILE}"
}

# ---------------------------------------------------------------------------
# Parameter echo
# ---------------------------------------------------------------------------
log INFO "=== Gaussian fitting pipeline ==="
log INFO "Root path : ${ROOT_PATH}"
log INFO "Data dir  : ${DATA_DIR}"
log INFO "Output dir: ${OUTPUT_DIR}"
log INFO "Threshold : ${THRESHOLD}"
log INFO "Rat ID    : ${RAT_ID}"
log INFO "Log file  : ${LOG_FILE}"

# ---------------------------------------------------------------------------
# Directory validation
# ---------------------------------------------------------------------------
if [ ! -d "${ROOT_PATH}" ]; then
    log ERROR "Root path does not exist: ${ROOT_PATH}"
    exit 1
fi

OUTPUT_FULL="${ROOT_PATH}/${OUTPUT_DIR#/}"
mkdir -p "${OUTPUT_FULL}"
log INFO "Output directory ensured: ${OUTPUT_FULL}"

# ---------------------------------------------------------------------------
# Python invocation
# ---------------------------------------------------------------------------
log INFO "Launching gaussian_tau_pipeline.py …"

python3 -c "
import sys
sys.path.insert(0, '${ROOT_PATH}/source')
from logging_config import setup_logging
setup_logging('${LOG_DIR}', 'DEBUG', 'gaussian_tau_pipeline_${RAT_ID}')
from gaussian_tau_pipeline import run_gaussian_fitting
rc = run_gaussian_fitting(
    '${ROOT_PATH}',
    '${DATA_DIR}',
    '${OUTPUT_DIR}',
    '${THRESHOLD}',
    '${RAT_ID}'
)
sys.exit(rc)
" 2>&1 | tee -a "${LOG_FILE}"

EXIT_CODE="${PIPESTATUS[0]}"
if [ "${EXIT_CODE}" -ne 0 ]; then
    log ERROR "Pipeline exited with code ${EXIT_CODE}."
    exit "${EXIT_CODE}"
fi

log INFO "=== Gaussian fitting complete for ${RAT_ID} ==="
exit 0
