#!/usr/bin/env bash
# =============================================================================
# batch_gaussian_fitting.sh
# =============================================================================
# Batch-run the Gaussian tau-fitting pipeline across rats and thresholds.
# Edit the configuration section below before running.
#
# Usage:
#   chmod +x scripts/batch_gaussian_fitting.sh
#   ./scripts/batch_gaussian_fitting.sh
#
# To run on a SLURM cluster choose op 1.
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration — edit these variables
# =============================================================================

ROOT_PATH="$1"
RATS="$2"                               # Space-separated: "R01 R02 R03 …"
MAP_GROUP="$3"                          # 1 = naïve group; 2 = alcohol group

REP="$4"                                # Number of repetitions
SLURM="$5"                              # SLURM on 1, off 0

THRESHOLD="0.0"                         # Space-separated for multiple: "0.0 0.2 0.4"
GROUP_NAME="t$(echo ${MAP_GROUP})"      # t1 or t2

FILTER_NAME="filter_kick_out"

# =============================================================================

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR="${ROOT_PATH}/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BATCH_LOG="${LOG_DIR}/batch_gaussian_${TIMESTAMP}.log"

log() {
    local level="$1"; shift
    echo "$(date +'%Y-%m-%d %H:%M:%S') [${level}] batch_gaussian_fitting.sh: $*" | tee -a "${BATCH_LOG}"
}

# ---------------------------------------------------------------------------
# Validate root
# ---------------------------------------------------------------------------

if [ ! -d "${ROOT_PATH}" ]; then
    log ERROR "Project root not found: ${ROOT_PATH}"
    exit 1
fi

cd "${ROOT_PATH}/scripts"

log INFO "=== Batch Gaussian fitting started ==="
log INFO "Root          : ${ROOT_PATH}"
log INFO "Group         : ${GROUP_NAME}"
log INFO "Thresholds    : ${THRESHOLD}"
log INFO "Rats          : ${RATS}"
log INFO "Repetitions   : ${REP}"
log INFO "SLURM         : ${SLURM}"

# ---------------------------------------------------------------------------
# Loop over repetitionsm thresholds and subjects
# ---------------------------------------------------------------------------

for r in $(seq 1 $REP); do
    for TH in ${THRESHOLD}; do
        for RAT in ${RATS}; do
            OUTPUT_DIR="/results/${GROUP_NAME}/FA_RN_SI_v0-1_th-${TH}/${FILTER_NAME}/${RAT}_r${r}"
            FULL_OUTPUT="${ROOT_PATH}/${OUTPUT_DIR#/}"

            DATA_DIR="/results/${GROUP_NAME}/FA_RN_SI_v0-1_th-0/${RAT}_r${r}"

            log INFO "Creating output directory: ${FULL_OUTPUT}"
            mkdir -p "${FULL_OUTPUT}"

            log INFO "Launching: rep=${r}, rat=${RAT}, threshold=${TH}"

            if [ "${SLURM}" -ne 1 ]; then
                # Direct execution (default)
                ./run_gaussian_fitting.sh \
                    "${ROOT_PATH}" \
                    "${DATA_DIR}" \
                    "${OUTPUT_DIR}" \
                    "${TH}" \
                    "${RAT}" \
                2>&1 | tee -a "${BATCH_LOG}"
            else
            # SLURM execution
            run -t 23:30 -c 1 -m 8 \
                -j "gauss_${RAT}_th${TH}" \
                ./run_gaussian_fitting.sh \
                    "${ROOT_PATH}" "${DATA_DIR}" "${OUTPUT_DIR}" "${TH}" "${RAT}"
            fi
        done
    done
done

log INFO "=== Batch Gaussian fitting complete ==="
exit 0
