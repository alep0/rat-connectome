"""
gaussian_tau_pipeline.py
========================
Compute tau (delay), velocity, distance, and fractional anisotropy
connectivity matrices by fitting Gaussian models to per-ROI-pair
fibre distributions.

Refactored from: Gaussian_fit_v1_3_n5.py

- Monitoring system memory in Python added.

"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from streamline_utils import load_dict, save_matrix_as_text

import psutil

logger = logging.getLogger(__name__)

# Physical constants
_DISTANCE_SCALE = 0.1 * 0.1 * (1.0 / 1000.0)   # integration step → metres
_VOXEL_ANISO = np.array([2.27273, 2.27273, 10.0])  # voxel dimensions (mm)


# ---------------------------------------------------------------------------
# Displays the memory stats in Gigabytes
# ---------------------------------------------------------------------------

def show_ram_usage():
    # Get virtual memory statistics
    mem = psutil.virtual_memory()
    
    # Convert bytes to GB for readability
    # (1 GB = 1024^3 bytes)
    used_gb = mem.used / (1024 ** 3)
    available_gb = mem.available / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    percent_used = mem.percent

    print("--- RAM Memory Status ---")
    print(f"Total:     {total_gb:.2f} GB")
    print(f"Used:      {used_gb:.2f} GB ({percent_used}%)")
    print(f"Available: {available_gb:.2f} GB")
    print("-------------------------")


# ---------------------------------------------------------------------------
# Histogram / tau computation
# ---------------------------------------------------------------------------

def compute_tau_per_roi_pair(
    streamlines: List[np.ndarray],
    velocities: List[np.ndarray],
    ax_data: List[np.ndarray],
    fm_data: List[np.ndarray],
    fr_data: List[np.ndarray],
    fa_data: List[np.ndarray],
    threshold: float,
    histogram_path: Optional[str] = None,
) -> Tuple[List[List[float]], List[float], List[float], List[float], List[float]]:
    """Compute tau (delay) and derived quantities for one ROI pair.

    For each fibre:
    - Length  ``d``   = physical arc length (metres)
    - Velocity ``v``  = median axon velocity (m/s) after filtering slow voxels
    - Tau ``τ``       = d / v

    Only fibres where the number of valid velocity voxels exceeds
    ``threshold * total_voxels`` are included.

    Parameters
    ----------
    streamlines:
        List of (N, 3) coordinate arrays for this ROI pair.
    velocities:
        Per-voxel velocity arrays (one per streamline).
    ax_data, fm_data, fr_data, fa_data:
        Per-voxel microstructural values (one array per streamline).
    threshold:
        Fractional filter: fibre included only if
        ``n_valid_voxels > threshold * total_voxels``.
    histogram_path:
        If provided, save a tau histogram PNG to this path.

    Returns
    -------
    Tuple
        ``(fiber_records, distances, velocities_median, taus, fa_medians)``
        ``fiber_records`` rows: ``[tau, d, v, ax_med, fm_med, fr_med, fa_med]``
    """
    fiber_records: List[List[float]] = []
    distances: List[float] = []
    vel_medians: List[float] = []
    taus: List[float] = []
    fa_medians: List[float] = []

    for idx in range(len(velocities)):
        raw_vel = velocities[idx]
        valid_vel = [v for v in raw_vel if v >= 1.0 and not np.isnan(v)]

        ax_vals = list(ax_data[idx])
        fm_vals = list(fm_data[idx])
        fr_vals = list(fr_data[idx])
        fa_vals = list(fa_data[idx])

        if len(valid_vel) <= round(len(raw_vel) * threshold):
            continue

        # Arc length
        arc_length = 0.0
        pts = streamlines[idx]
        for z in range(len(pts) - 1):
            diff = pts[z + 1] - pts[z]
            arc_length += np.linalg.norm(_VOXEL_ANISO * diff)
        arc_length *= _DISTANCE_SCALE

        v_med = float(np.median(valid_vel))
        tau = arc_length / v_med
        fa_med = float(np.median(fa_vals))

        taus.append(tau)
        distances.append(arc_length)
        vel_medians.append(v_med)
        fa_medians.append(fa_med)

        fiber_records.append([
            tau, arc_length, v_med,
            float(np.median(ax_vals)),
            float(np.median(fm_vals)),
            float(np.median(fr_vals)),
            fa_med,
        ])

    logger.debug("compute_tau_per_roi_pair: %d fibres accepted.", len(fiber_records))

    if histogram_path and taus:
        fig, ax = plt.subplots()
        ax.hist(taus)
        ax.set_xlabel("tau (s)")
        ax.set_ylabel("Count (fibres)")
        plt.tight_layout()
        plt.savefig(histogram_path)
        plt.close(fig)
        logger.info("Tau histogram saved → %s", histogram_path)

    return fiber_records, distances, vel_medians, taus, fa_medians


# ---------------------------------------------------------------------------
# Main fitting pipeline
# ---------------------------------------------------------------------------

def run_gaussian_fitting(
    root: str,
    data_dir: str,
    output_dir: str,
    threshold: str,
    rat: str,
) -> int:
    """Compute tau / W / D / V / FA matrices for one subject.

    Parameters
    ----------
    root:
        Project root directory path.
    data_dir:
        Relative path to the per-rat streamline/velocity dictionaries
        (output of the connectome matrix pipeline).
    output_dir:
        Relative path for outputs.
    threshold:
        Fibre filter threshold (string, e.g. ``"0.0"``).
    rat:
        Subject identifier (e.g. ``"R01"``).

    Returns
    -------
    int
        0 on success.
    """
    t_start = time.time()
    root_path = Path(root)
    in_path = root_path / data_dir.lstrip("/")
    out_path = root_path / output_dir.lstrip("/")
    out_path.mkdir(parents=True, exist_ok=True)

    th = float(threshold)
    logger.info("=== Gaussian fitting start: rat=%s, th=%s ===", rat, threshold)

    roi_i = [8, 12, 70]
    roi_j = [29, 91]

    #roi_i = [*range(3, 79, 1)] + [*range(78 + 3 + 1, 78 + 78 + 1, 1)]
    #roi_j = roi_i

    N_BINS = 20
    N_NODES = 79
    mat_size = 2 * N_NODES

    w_mat = np.zeros((mat_size, mat_size))
    d_mat = np.zeros((mat_size, mat_size))
    v_mat = np.zeros((mat_size, mat_size))
    tau_mat = np.zeros((mat_size, mat_size))
    fa_mat = np.zeros((mat_size, mat_size))

    fiber_records_all: Dict = {}

    for i in roi_i:
        for j in roi_j:
            if j <= i:
                continue

            logger.info("Processing ROI pair (%d, %d).", i, j)
            
            show_ram_usage()

            vel_dic = load_dict(str(in_path / f"Velocities_{rat}_ij_{i}-{j}.dat"))
            stm_dic = load_dict(str(in_path / f"Streamlines_{rat}_ij_{i}-{j}.dat"))
            ax_dic  = load_dict(str(in_path / f"AX_{rat}_ij_{i}-{j}.dat"))
            fm_dic  = load_dict(str(in_path / f"FM_{rat}_ij_{i}-{j}.dat"))
            fr_dic  = load_dict(str(in_path / f"FR_{rat}_ij_{i}-{j}.dat"))
            fa_dic  = load_dict(str(in_path / f"FA_{rat}_ij_{i}-{j}.dat"))

            if not vel_dic:
                logger.warning("No velocity data for pair (%d, %d); skipping.", i, j)
                continue

            hist_path = str(
                out_path / f"Histogram_tau_fibre_{rat}_ij_{i}-{j}.png"
            )

            records, dists, vels, taus, fas = compute_tau_per_roi_pair(
                stm_dic.get((i, j), []),
                vel_dic.get((i, j), []),
                ax_dic.get((i, j), []),
                fm_dic.get((i, j), []),
                fr_dic.get((i, j), []),
                fa_dic.get((i, j), []),
                th,
                hist_path,
            )

            if records:
                fiber_records_all[i, j] = records
                w_mat[i, j] = len(dists)
                d_mat[i, j] = float(np.median(dists))
                v_mat[i, j] = float(np.median(vels))
                tau_mat[i, j] = float(np.median(taus))
                fa_mat[i, j] = float(np.median(fas))

    # Save fibre records dictionary
    import pickle
    rec_path = out_path / f"th-{threshold}_{rat}_b{N_BINS}_fibre_records.dat"
    with open(rec_path, "wb") as fh:
        pickle.dump(fiber_records_all, fh)
    logger.info("Fibre records saved → %s", rec_path)

    # Save matrices
    prefix = str(out_path / f"th-{threshold}_{rat}")
    for name, mat in [("w", w_mat), ("d", d_mat), ("v", v_mat),
                      ("tau", tau_mat), ("fa", fa_mat)]:
        save_matrix_as_text(mat, f"{prefix}_{name}.txt")

    elapsed = (time.time() - t_start) / 60.0
    logger.info("Gaussian fitting complete in %.2f min.", elapsed)
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute tau / connectivity matrices for one subject."
    )
    parser.add_argument("--root",       required=True, help="Project root path")
    parser.add_argument("--data-dir",   required=True, help="Relative path to input dictionaries")
    parser.add_argument("--output-dir", required=True, help="Relative output path")
    parser.add_argument("--threshold",  default="0.0", help="Fibre filter threshold")
    parser.add_argument("--rat",        required=True, help="Subject ID (e.g. R01)")
    parser.add_argument("--log-level",  default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    sys.exit(
        run_gaussian_fitting(
            args.root, args.data_dir, args.output_dir,
            args.threshold, args.rat,
        )
    )
