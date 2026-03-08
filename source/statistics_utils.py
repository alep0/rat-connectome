"""
statistics_utils.py
====================
Statistical comparison utilities: empirical CDFs, boxplots,
Kolmogorov–Smirnov test, Mann–Whitney U test, and Cohen's d.

Refactored from: statistics_v2.py
"""

import logging
from pathlib import Path
from typing import List, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ks_2samp, mannwhitneyu

logger = logging.getLogger(__name__)


def cohens_d(x: Sequence[float], y: Sequence[float]) -> float:
    """Compute Cohen's d effect size using pooled standard deviation.

    Parameters
    ----------
    x, y:
        Two samples to compare.

    Returns
    -------
    float
        Cohen's d. Returns 0.0 if pooled standard deviation is zero.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        logger.warning("cohens_d: insufficient sample sizes (%d, %d).", nx, ny)
        return 0.0

    pooled_var = ((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2)
    pooled_std = np.sqrt(pooled_var)
    if pooled_std == 0.0:
        logger.warning("cohens_d: pooled std is 0; returning 0.")
        return 0.0

    return float((np.mean(x) - np.mean(y)) / pooled_std)


def analyze_and_plot(
    data1: Sequence[float],
    data2: Sequence[float],
    label1: str,
    label2: str,
    output_dir: Path,
    variable_name: str,
) -> dict:
    """Run statistical tests and save CDF + boxplot figures.

    Saves two PNG files:
    - ``{label1}vs{label2}_CDF_{variable_name}.png``
    - ``{label1}vs{label2}_boxplots_{variable_name}.png``

    Parameters
    ----------
    data1, data2:
        Samples to compare.
    label1, label2:
        Human-readable labels for each sample.
    output_dir:
        Directory where figures are saved.
    variable_name:
        Axis label for the measured quantity.

    Returns
    -------
    dict
        ``{"ks_stat", "ks_p", "mw_stat", "mw_p", "cohens_d"}``
    """
    data1, data2 = list(data1), list(data2)

    if not data1 or not data2:
        logger.error("analyze_and_plot: one or both datasets are empty.")
        return {}

    # --- Empirical CDF -------------------------------------------------------
    x1 = np.sort(data1)
    y1 = np.arange(1, len(x1) + 1) / len(x1)
    x2 = np.sort(data2)
    y2 = np.arange(1, len(x2) + 1) / len(x2)

    fig_cdf, ax_cdf = plt.subplots(figsize=(7, 5))
    ax_cdf.plot(x1, y1, color="blue", label=label1)
    ax_cdf.plot(x2, y2, color="red", label=label2)
    ax_cdf.set_xlabel(variable_name)
    ax_cdf.set_ylabel("ECDF")
    ax_cdf.set_title("Empirical CDFs")
    ax_cdf.grid(True)
    ax_cdf.legend()
    fig_cdf.tight_layout()

    cdf_path = output_dir / f"{label1}vs{label2}_CDF_{variable_name}.png"
    fig_cdf.savefig(str(cdf_path))
    plt.close(fig_cdf)
    logger.info("CDF figure saved → %s", cdf_path)

    # --- Statistical tests ---------------------------------------------------
    ks_stat, ks_p = ks_2samp(data1, data2)
    mw_stat, mw_p = mannwhitneyu(data1, data2, alternative="two-sided")
    d = cohens_d(data1, data2)

    logger.info(
        "Stats [%s vs %s | %s]: KS p=%.4f, MW p=%.4f, d=%.4f",
        label1, label2, variable_name, ks_p, mw_p, d,
    )

    # --- Boxplot -------------------------------------------------------------
    annotation = (
        f"KS p-value = {ks_p:.4f}\n"
        f"Mann–Whitney p-value = {mw_p:.4f}\n"
        f"Cohen's d = {d:.4f}"
    )

    fig_box, ax_box = plt.subplots(figsize=(7, 5))
    ax_box.boxplot([data1, data2], labels=[label1, label2])
    ax_box.set_title("Boxplots with Statistical Results")
    ax_box.set_ylabel(variable_name)
    ax_box.grid(True)
    ax_box.text(
        1.05, 0.95, annotation,
        transform=ax_box.transAxes,
        verticalalignment="top",
        fontsize=10,
        bbox=dict(facecolor="white", alpha=0.7),
    )
    fig_box.tight_layout()

    box_path = output_dir / f"{label1}vs{label2}_boxplots_{variable_name}.png"
    fig_box.savefig(str(box_path))
    plt.close(fig_box)
    logger.info("Boxplot figure saved → %s", box_path)

    return {
        "ks_stat": ks_stat, "ks_p": ks_p,
        "mw_stat": mw_stat, "mw_p": mw_p,
        "cohens_d": d,
    }


# ---------------------------------------------------------------------------
# CLI example / smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Example statistics run with synthetic data.")
    parser.add_argument("--output-dir", default="/tmp/stats_example")
    parser.add_argument("--log-level",  default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    d1 = rng.standard_normal(200).tolist()
    d2 = (rng.standard_normal(200) + 0.5).tolist()

    results = analyze_and_plot(d1, d2, "group_A", "group_B", out, "random_variable")
    print("Results:", results)
