#!/usr/bin/env bash
# =============================================================================
# batch_connectome_matrix.sh
# =============================================================================
# Batch-run the connectome matrix pipeline for all subjects.
# Edit the configuration section below before running.
#
# Usage:
#   chmod +x scripts/batch_connectome_matrix.sh
#   ./scripts/batch_connectome_matrix.sh
#
# To run on SLURM, uncomment the `#run` lines.
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration — edit these variables
# =============================================================================
ROOT_PATH="$1"       # root_path/rat-connectome
RATS="$2"            # Space-separated: "R01 R02 R03 …"
THRESHOLD="0.0"
PLOT_ON=0            # 0 = off (recommended for cluster); 1 = on (requires display)
MAP_GROUP=1          # 1 = naïve group; 2 = alcohol group
GROUP="t$(echo ${MAP_GROUP})"   # t1 or t2

DIRECTORY_NAME="FA_RN_SI_v0-1_th-0"
# =============================================================================

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR="${ROOT_PATH}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BATCH_LOG="${LOG_DIR}/batch_connectome_${TIMESTAMP}.log"

log() {
    local level="$1"; shift
    echo "$(date +'%Y-%m-%d %H:%M:%S') [${level}] batch_connectome_matrix.sh: $*" | tee -a "${BATCH_LOG}"
}

# ---------------------------------------------------------------------------
# Validate root
# ---------------------------------------------------------------------------
if [ ! -d "${ROOT_PATH}" ]; then
    log ERROR "Project root not found: ${ROOT_PATH}"
    exit 1
fi

cd "${ROOT_PATH}/scripts"

log INFO "=== Batch connectome matrix started ==="
log INFO "Root   : ${ROOT_PATH}"
log INFO "Group  : ${GROUP}"
log INFO "Rats   : ${RATS}"

# ---------------------------------------------------------------------------
# Loop over subjects
# ---------------------------------------------------------------------------
for RAT in ${RATS}; do
    DATA_PATH="/data/raw/${GROUP}/${RAT}"
    FIGURES_PATH="/results/${GROUP}/${DIRECTORY_NAME}/${RAT}"
    FULL_FIGURES="${ROOT_PATH}/${FIGURES_PATH#/}"

    log INFO "Creating output directory: ${FULL_FIGURES}"
    mkdir -p "${FULL_FIGURES}"

    log INFO "Launching: rat=${RAT}, group=${GROUP}"

    # Direct execution (default)
    ./run_connectome_matrix.sh \
        "${ROOT_PATH}" \
        "${DATA_PATH}" \
        "${FIGURES_PATH}" \
        "${GROUP}" \
        "${RAT}" \
        "${THRESHOLD}" \
        "${PLOT_ON}" \
        "${MAP_GROUP}" \
        2>&1 | tee -a "${BATCH_LOG}"

    # SLURM execution (uncomment to use):
    # run -t 123:30 -c 1 -m 16 \
    #     -j "matrices_${RAT}" \
    #     ./run_connectome_matrix.sh \
    #         "${ROOT_PATH}" "${DATA_PATH}" "${FIGURES_PATH}" \
    #         "${GROUP}" "${RAT}" "${THRESHOLD}" "${PLOT_ON}" "${MAP_GROUP}"

done

log INFO "=== Batch connectome matrix complete ==="
exit 0
