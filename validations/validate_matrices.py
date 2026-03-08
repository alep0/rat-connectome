"""
validate_matrices.py
=====================
Validate the shape, symmetry, non-negativity, and expected value ranges
of connectivity matrices produced by the pipelines.

Run as:
    python3 validations/validate_matrices.py \
        --root /workspace/connectome \
        --results-dir results/t1/FA_RN_SI_v0-1_th-0.0/filter_kick_out \
        --rat R01 \
        --threshold 0.0
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

EXPECTED_SIZE = 158   # 2 * 79 ROIs
VARIABLE_RANGES = {
    "w":   (0.0, 1e6),    # fibre count — non-negative
    "d":   (0.0, 10.0),   # distance (m) — reasonable brain scale
    "v":   (0.0, 100.0),  # velocity (m/s)
    "tau": (0.0, 100.0),  # delay (s)
    "fa":  (0.0, 1.0),    # fractional anisotropy
}


def load_matrix(path: Path) -> Optional[np.ndarray]:
    """Load a whitespace-delimited matrix file."""
    try:
        mat = np.loadtxt(str(path))
        logger.debug("Loaded matrix: %s (shape %s)", path, mat.shape)
        return mat
    except Exception as exc:
        logger.error("Cannot load matrix %s: %s", path, exc)
        return None


def check_shape(mat: np.ndarray, name: str) -> bool:
    """Check that the matrix is square and of expected size."""
    ok = mat.ndim == 2 and mat.shape[0] == mat.shape[1] == EXPECTED_SIZE
    status = "OK" if ok else "FAIL"
    logger.info("[%s] %s shape: %s (expected %d×%d)",
                status, name, mat.shape, EXPECTED_SIZE, EXPECTED_SIZE)
    return ok


def check_non_negative(mat: np.ndarray, name: str) -> bool:
    """Check that no matrix entries are negative."""
    ok = bool(np.all(mat >= 0))
    status = "OK" if ok else "FAIL"
    n_neg = int(np.sum(mat < 0))
    logger.info("[%s] %s non-negative: %d negative entries", status, name, n_neg)
    return ok


def check_upper_triangle_only(mat: np.ndarray, name: str) -> bool:
    """Verify that the lower triangle (and diagonal) are all zero."""
    lower = np.tril(mat)
    ok = bool(np.allclose(lower, 0))
    status = "OK" if ok else "WARN"
    log_fn = logger.info if ok else logger.warning
    log_fn("[%s] %s lower-triangle zeros: max abs = %.4e",
           status, name, float(np.abs(lower).max()))
    return ok


def check_value_range(mat: np.ndarray, name: str,
                      lo: float, hi: float) -> bool:
    """Check that all non-zero upper-triangle values fall within [lo, hi]."""
    upper_vals = [mat[i, j] for i in range(len(mat))
                  for j in range(len(mat))
                  if j > i and mat[i, j] != 0]
    if not upper_vals:
        logger.warning("[SKIP] %s: no non-zero upper-triangle entries.", name)
        return True

    arr = np.array(upper_vals)
    ok = bool(np.all((arr >= lo) & (arr <= hi)))
    status = "OK" if ok else "WARN"
    log_fn = logger.info if ok else logger.warning
    log_fn("[%s] %s value range: min=%.4f, max=%.4f (expected [%.1f, %.1f])",
           status, name, float(arr.min()), float(arr.max()), lo, hi)
    return ok


def validate_matrices(root: str, results_dir: str, rat: str, threshold: str) -> int:
    """Run all matrix validation checks for a single subject.

    Parameters
    ----------
    root:
        Project root directory.
    results_dir:
        Relative path to the subject results directory.
    rat:
        Subject identifier.
    threshold:
        Threshold string used in filenames.

    Returns
    -------
    int
        0 if all checks pass, 1 otherwise.
    """
    root_path = Path(root)
    rat_dir = root_path / results_dir.lstrip("/") / rat

    logger.info("=" * 60)
    logger.info("Matrix validation — rat=%s, dir=%s", rat, rat_dir)
    logger.info("=" * 60)

    all_passed = True

    for var, (lo, hi) in VARIABLE_RANGES.items():
        filename = f"th-{threshold}_{rat}_{var}.txt"
        filepath = rat_dir / filename

        if not filepath.exists():
            logger.warning("[SKIP] %s not found: %s", var, filepath)
            continue

        mat = load_matrix(filepath)
        if mat is None:
            all_passed = False
            continue

        checks = [
            check_shape(mat, var),
            check_non_negative(mat, var),
            check_upper_triangle_only(mat, var),
            check_value_range(mat, var, lo, hi),
        ]
        if not all(checks):
            all_passed = False

    logger.info("=" * 60)
    status = "PASSED" if all_passed else "FAILED (see warnings above)"
    logger.info("Matrix validation: %s", status)
    logger.info("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate connectivity matrices.")
    parser.add_argument("--root",        required=True, help="Project root path")
    parser.add_argument("--results-dir", required=True, help="Relative results directory")
    parser.add_argument("--rat",         required=True, help="Subject ID (e.g. R01)")
    parser.add_argument("--threshold",   default="0.0")
    parser.add_argument("--log-level",   default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    sys.exit(
        validate_matrices(
            args.root, args.results_dir, args.rat, args.threshold
        )
    )
