"""
structural_connectivity_analysis.py
=====================================
Group-level structural connectivity analysis: load per-subject matrices,
apply group masks, compute ensemble statistics, and save figures.

Refactored from: statistics_structural_connectivity_engine_v4.py
"""

import logging
#import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.colors import ListedColormap

from statistics_utils import analyze_and_plot

logger = logging.getLogger(__name__)

ALL_RATS = [
    "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10",
    "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
]


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_matrix(directory: Path, filename: str) -> np.ndarray:
    """Load a whitespace-delimited connectivity matrix from disk.

    Parameters
    ----------
    directory:
        Parent directory.
    filename:
        File name inside *directory*.

    Returns
    -------
    np.ndarray
        Loaded 2-D array.

    Raises
    ------
    FileNotFoundError
        If the file cannot be read.
    """
    filepath = directory / filename
    try:
        matrix = np.loadtxt(str(filepath))
        logger.debug("Matrix loaded from %s", filepath)
        return matrix
    except Exception as exc:
        raise FileNotFoundError(
            f"Failed to load matrix from {filepath}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Mask utilities
# ---------------------------------------------------------------------------

def matrix_to_vector(matrix: np.ndarray, threshold: float = 0.0) -> List[float]:
    """Flatten the upper triangle of a matrix into a list of values > threshold.

    Parameters
    ----------
    matrix:
        2-D connectivity matrix.
    threshold:
        Only values strictly above this are included.

    Returns
    -------
    List[float]
    """
    N = len(matrix)
    return [
        matrix[i, j]
        for i in range(N)
        for j in range(N)
        if j > i and matrix[i, j] > threshold
    ]


def apply_mask(matrix: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Element-wise multiply upper-triangle entries of *matrix* by *mask*.

    Parameters
    ----------
    matrix:
        Input connectivity matrix (modified in place and returned).
    mask:
        Binary mask of the same shape.

    Returns
    -------
    np.ndarray
        Masked matrix.
    """
    N = len(matrix)
    for i in range(N):
        for j in range(N):
            if j > i:
                matrix[i, j] *= mask[i, j]
    return matrix


def compute_group_mask(
    rats: List[str],
    data_path: Path,
    fibre_threshold: int,
    rat_threshold: int,
) -> np.ndarray:
    """Build a group connectivity mask.

    A connection (i, j) is included if at least *rat_threshold* subjects
    have ``W[i, j] > fibre_threshold``.

    Parameters
    ----------
    rats:
        List of subject identifiers.
    data_path:
        Directory containing per-subject ``th-0.0_{rat}_w.txt`` files.
    fibre_threshold:
        Minimum fibre count for a connection to be considered present.
    rat_threshold:
        Minimum number of subjects with the connection present.

    Returns
    -------
    np.ndarray
        Binary mask.
    """
    per_rat_masks: Dict[str, np.ndarray] = {}

    for rat in rats:
        try:
            w_mat = load_matrix(data_path / rat, f"th-0.0_{rat}_w.txt")
        except FileNotFoundError as exc:
            logger.warning("Skipping rat %s: %s", rat, exc)
            continue

        N = len(w_mat)
        mask = np.zeros((N, N))
        for i in range(N):
            for j in range(N):
                if j > i and w_mat[i, j] > fibre_threshold:
                    mask[i, j] = 1
        per_rat_masks[rat] = mask

    if not per_rat_masks:
        logger.error("No valid rat data found; cannot build group mask.")
        return np.zeros((1, 1))

    sample = next(iter(per_rat_masks.values()))
    N = len(sample)
    group_mask = np.zeros((N, N))

    for i in range(N):
        for j in range(N):
            if j > i:
                count = sum(
                    per_rat_masks[r][i, j]
                    for r in per_rat_masks
                )
                if count >= rat_threshold:
                    group_mask[i, j] = 1

    n_connections = int(group_mask.sum())
    logger.info("Group mask: %d connections (fibre_th=%d, rat_th=%d).",
                n_connections, fibre_threshold, rat_threshold)
    return group_mask


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_connectivity_matrix(
    matrix: np.ndarray,
    output_dir: Path,
    name: str,
    color_limit: float,
    mode: str = "cor",
    saturation: str = "no",
) -> None:
    """Save a heatmap of a connectivity matrix.

    Parameters
    ----------
    matrix:
        2-D array to visualise.
    output_dir:
        Output directory.
    name:
        Figure title and filename stem.
    color_limit:
        Upper colour-scale limit (used in ``"con"`` + ``"sat"`` mode).
    mode:
        ``"gen"`` — generic coolwarm; ``"cor"`` — correlation [−1, 1];
        ``"con"`` — connectivity with white-zero colourmap.
    saturation:
        ``"sat"`` to saturate at *color_limit*; anything else for auto-range.
    """
    fig = plt.figure(figsize=(8, 6))

    if mode == "gen":
        sns.heatmap(matrix, cmap="coolwarm", square=True)
    elif mode == "cor":
        sns.heatmap(matrix, cmap="coolwarm", vmin=-1, vmax=1, square=True)
    else:
        viridis = plt.cm.viridis(np.linspace(0, 1, 255))
        colors = np.vstack(([[1, 1, 1, 1]], viridis))
        cmap = ListedColormap(colors)
        if saturation == "sat":
            sns.heatmap(matrix, cmap=cmap, vmin=0, vmax=color_limit,
                        cbar=True, square=True)
        else:
            sns.heatmap(matrix, cmap=cmap, cbar=True, square=True)

    plt.title(name)
    plt.xlabel("ROI")
    plt.ylabel("ROI")
    plt.tight_layout()

    save_path = output_dir / f"{name}_matrix.png"
    fig.savefig(str(save_path))
    plt.close(fig)
    logger.info("Matrix heatmap saved → %s", save_path)


def plot_histogram(
    matrix: np.ndarray,
    output_dir: Path,
    name: str,
    scale: str = "linear",
    x_limit: float = None,
) -> None:
    """Save a histogram of upper-triangle values from *matrix*.

    Parameters
    ----------
    matrix:
        2-D connectivity matrix.
    output_dir:
        Output directory.
    name:
        Figure title and filename stem.
    scale:
        ``"log"`` for logarithmic y-axis; ``"linear"`` (default) otherwise.
    x_limit:
        Upper bound for the histogram x-axis. ``None`` for auto.
    """
    vector = matrix_to_vector(matrix)
    if not vector:
        logger.warning("plot_histogram: empty vector for '%s'.", name)
        return

    fig, ax = plt.subplots()
    hist_kwargs = dict(bins=50, color="burlywood")
    if x_limit is not None:
        hist_kwargs["range"] = (0, x_limit)
    ax.hist(vector, **hist_kwargs)

    if scale == "log":
        ax.set_yscale("log")

    ax.set_xlabel(name)
    ax.set_ylabel("Frequency (ROI pairs)")
    fig.tight_layout()

    save_path = output_dir / f"{name}_hist.png"
    fig.savefig(str(save_path))
    plt.close(fig)
    logger.info("Histogram saved → %s", save_path)


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------

def run_group_analysis(
    root: str,
    output_name: str,
    model_name_1: str,
    group_name_1: str,
    model_name_2: str,
    group_name_2: str,
    variable: str,
    color_limit: float,
    log_scale: int,
    scale_factor: float,
    rats: Optional[List[str]] = None,
) -> None:
    """Compare two groups' structural connectivity for one variable.

    Parameters
    ----------
    root:
        Project root directory.
    output_name:
        Sub-directory in ``results/`` for outputs.
    model_name_1, model_name_2:
        Filter/model labels for each group.
    group_name_1, group_name_2:
        Group labels (e.g. ``"t1"``, ``"t2"``).
    variable:
        Matrix variable name (``"w"``, ``"d"``, ``"v"``, ``"tau"``, ``"fa"``).
    color_limit:
        Heatmap saturation limit.
    log_scale:
        1 for logarithmic histogram y-axis, 0 for linear.
    scale_factor:
        Multiplicative factor applied to matrix values before plotting.
    rats:
        Subject list. Defaults to all 18 subjects.
    """
    if rats is None:
        rats = ALL_RATS

    root_path = Path(root)
    output_dir = root_path / "results" / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    base = root_path / "results"

    def _data_path(group: str, model: str) -> Path:
        return base / group / "FA_RN_SI_v0-1_th-0.0" / model

    logger.info("Computing group masks …")
    mask_1 = compute_group_mask(rats, _data_path(group_name_1, model_name_1), 50, 18)
    #mask_2 = compute_group_mask(rats, _data_path(group_name_2, model_name_2), 50, 18)
    logger.info("Group masks computed.")

    ensemble_1: List[float] = []
    ensemble_2: List[float] = []

    scale = "log" if log_scale else "linear"

    for rat in rats:
        dir_1 = _data_path(group_name_1, model_name_1) / rat
        dir_2 = _data_path(group_name_2, model_name_2) / rat

        try:
            mat_1 = load_matrix(dir_1, f"th-0.0_{rat}_{variable}.txt")
            mat_2 = load_matrix(dir_2, f"th-0.0_{rat}_{variable}.txt")
        except FileNotFoundError as exc:
            logger.warning("Skipping rat %s: %s", rat, exc)
            continue

        masked_1 = apply_mask(mat_1.copy(), mask_1)
        masked_2 = apply_mask(mat_2.copy(), mask_1)   # both masked by group-1 mask

        label_1 = f"{model_name_1}_{group_name_1}_{rat}"
        label_2 = f"{model_name_2}_{group_name_2}_{rat}"

        plot_connectivity_matrix(
            masked_1 * scale_factor, output_dir, f"{label_1}_{variable}",
            color_limit, "con", "sat"
        )
        plot_histogram(masked_1 * scale_factor, output_dir,
                       f"{label_1}_{variable}", scale, color_limit)

        plot_connectivity_matrix(
            masked_2 * scale_factor, output_dir, f"{label_2}_{variable}",
            color_limit, "con", "sat"
        )
        plot_histogram(masked_2 * scale_factor, output_dir,
                       f"{label_2}_{variable}", scale, color_limit)

        vec_1 = matrix_to_vector(masked_1 * scale_factor)
        vec_2 = matrix_to_vector(masked_2 * scale_factor)

        analyze_and_plot(vec_1, vec_2, label_1, label_2, output_dir, variable)

        ensemble_1.extend(vec_1)
        ensemble_2.extend(vec_2)

    # Ensemble comparison
    ens_label_1 = f"{model_name_1}_{group_name_1}_ensemble"
    ens_label_2 = f"{model_name_2}_{group_name_2}_ensemble"
    analyze_and_plot(ensemble_1, ensemble_2, ens_label_1, ens_label_2, output_dir, variable)
    logger.info("Group analysis complete for variable '%s'.", variable)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Group-level structural connectivity analysis."
    )
    parser.add_argument("--root",         required=True)
    parser.add_argument("--output-name",  required=True)
    parser.add_argument("--model-1",      default="filter_kick_out")
    parser.add_argument("--group-1",      default="t1")
    parser.add_argument("--model-2",      default="filter_kick_out")
    parser.add_argument("--group-2",      default="t2")
    parser.add_argument("--variable",     default="w",
                        choices=["w", "d", "v", "tau", "fa"])
    parser.add_argument("--color-limit",  type=float, default=8000.0)
    parser.add_argument("--log-scale",    type=int,   default=0)
    parser.add_argument("--scale-factor", type=float, default=1.0)
    parser.add_argument("--log-level",    default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run_group_analysis(
        args.root, args.output_name,
        args.model_1, args.group_1,
        args.model_2, args.group_2,
        args.variable, args.color_limit,
        args.log_scale, args.scale_factor,
    )
