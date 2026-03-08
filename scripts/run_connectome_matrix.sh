#!/usr/bin/env bash
# =============================================================================
# run_connectome_matrix.sh
# =============================================================================
# Run the connectome matrix computation pipeline for a single subject.
#
# Usage:
#   chmod +x scripts/run_connectome_matrix.sh
#   ./scripts/run_connectome_matrix.sh \
#       <root_path> <data_path> <figures_path> \
#       <group> <rat_id> <threshold> <plot_on> <map_group>
#
# Arguments:
#   root_path    - Absolute path to project root
#   data_path    - Relative path to subject DWI data (e.g. /data/raw/t1/R01)
#   figures_path - Relative path for outputs (e.g. /results/t1/FA_RN_SI_v0-1_th-0/R01)
#   group        - Experimental group (e.g. t1)
#   rat_id       - Subject identifier (e.g. R01)
#   threshold    - Fibre filter threshold (e.g. 0.0)
#   plot_on      - Enable 3D plots: 1 = yes, 0 = no
#   map_group    - Microstructural map prefix: 1 = naïve, 2 = alcohol
#
# Example:
#   ./scripts/run_connectome_matrix.sh \
#       /workspace/connectome \
#       /data/raw/t1/R01 \
#       /results/t1/FA_RN_SI_v0-1_th-0/R01 \
#       t1 R01 0.0 0 1
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------
if [ "$#" -ne 8 ]; then
    echo "[ERROR] Expected 8 arguments, got $#."
    echo "Usage: $0 <root_path> <data_path> <figures_path> <group> <rat_id> <threshold> <plot_on> <map_group>"
    exit 1
fi

ROOT_PATH="$1"
DATA_PATH="$2"
FIGURES_PATH="$3"
GROUP="$4"
RAT_ID="$5"
THRESHOLD="$6"
PLOT_ON="$7"
MAP_GROUP="$8"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR="${ROOT_PATH}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/connectome_matrix_${RAT_ID}_${TIMESTAMP}.log"

log() {
    local level="$1"; shift
    echo "$(date +'%Y-%m-%d %H:%M:%S') [${level}] run_connectome_matrix.sh: $*" | tee -a "${LOG_FILE}"
}

# ---------------------------------------------------------------------------
# Parameter echo
# ---------------------------------------------------------------------------
log INFO "=== Connectome matrix pipeline ==="
log INFO "Root path    : ${ROOT_PATH}"
log INFO "Data path    : ${DATA_PATH}"
log INFO "Figures path : ${FIGURES_PATH}"
log INFO "Group        : ${GROUP}"
log INFO "Rat ID       : ${RAT_ID}"
log INFO "Threshold    : ${THRESHOLD}"
log INFO "Plot 3D      : ${PLOT_ON}"
log INFO "Map group    : ${MAP_GROUP}"
log INFO "Log file     : ${LOG_FILE}"

# ---------------------------------------------------------------------------
# Validate and prepare directories
# ---------------------------------------------------------------------------
if [ ! -d "${ROOT_PATH}" ]; then
    log ERROR "Root path does not exist: ${ROOT_PATH}"
    exit 1
fi

FIGURES_FULL="${ROOT_PATH}/${FIGURES_PATH#/}"
mkdir -p "${FIGURES_FULL}"
log INFO "Output directory ensured: ${FIGURES_FULL}"

# ---------------------------------------------------------------------------
# Python invocation
# ---------------------------------------------------------------------------
log INFO "Launching connectome_matrix_pipeline.py …"

python3 -c "
import sys
sys.path.insert(0, '${ROOT_PATH}/source')
from logging_config import setup_logging
setup_logging('${LOG_DIR}', 'DEBUG', 'connectome_matrix_${RAT_ID}')
from connectome_matrix_pipeline import run_pipeline
rc = run_pipeline(
    '${ROOT_PATH}',
    '${DATA_PATH}',
    '${FIGURES_PATH}',
    '${GROUP}',
    '${RAT_ID}',
    '${THRESHOLD}',
    '${PLOT_ON}',
    '${MAP_GROUP}'
)
sys.exit(rc)
" 2>&1 | tee -a "${LOG_FILE}"

EXIT_CODE="${PIPESTATUS[0]}"
if [ "${EXIT_CODE}" -ne 0 ]; then
    log ERROR "Pipeline exited with code ${EXIT_CODE}."
    exit "${EXIT_CODE}"
fi

log INFO "=== Connectome matrix pipeline complete for ${RAT_ID} ==="
exit 0
