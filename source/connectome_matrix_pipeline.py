"""
connectome_matrix_pipeline.py
==============================
Compute W (fibre count), D (median fibre length), and V (median velocity)
connectivity matrices from diffusion-weighted MRI data.

Refactored from: Streamlines_W_D_V_T_v2_16_n3.py
"""

import logging
import sys
import time
from pathlib import Path
from typing import List#, Optional

import matplotlib.pyplot as plt
import numpy as np

# Dipy imports — require the ``conn_env`` conda environment
from dipy.core.gradients import gradient_table
from dipy.data import default_sphere
from dipy.denoise.patch2self import patch2self
from dipy.direction import peaks_from_model
from dipy.io.image import load_nifti, load_nifti_data
from dipy.reconst.dti import TensorModel, fractional_anisotropy
from dipy.reconst.shm import CsaOdfModel
from dipy.tracking import utils as tracking_utils
from dipy.tracking.local_tracking import LocalTracking
from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
from dipy.tracking.streamline import Streamlines
#from dipy.viz import actor, colormap, has_fury, window
from numpy import loadtxt

from streamline_utils import (
    build_velocity_volume,
    clean_streamlines,
    compute_velocities,
    get_roi_streamlines,
    #load_dict,
    plot_coronal_slices,
    plot_streamlines_3d,
    save_dict,
    save_matrix_as_text,
)

logger = logging.getLogger(__name__)

# Physical voxel-size scaling constants  [mm → m conversion]
_VOXEL_SCALE = np.array([2.27273, 2.27273, 10.0])
_SPEED_SCALE = 0.1 * 0.1 * (1.0 / 1000.0)


# ---------------------------------------------------------------------------
# Atlas loading
# ---------------------------------------------------------------------------

def load_atlas(root: Path) -> tuple:
    """Load the coarse-grain atlas labels and ROI names.

    Parameters
    ----------
    root:
        Project root directory. Expects:
        ``root/data/raw/atlas_cg_3d5_list.txt`` and
        ``root/data/raw/atlas_cg_3d5_names.txt``.

    Returns
    -------
    Tuple[List[List[int]], List[str]]
        ``(atlas_cg, roi_names)``
    """
    list_path = root / "data" / "raw" / "atlas_cg_3d5_list.txt"
    names_path = root / "data" / "raw" / "atlas_cg_3d5_names.txt"

    with list_path.open("r") as fh:
        raw = fh.read()

    entries = raw.split("x")
    atlas_cg: List[List[int]] = [[] for _ in range(len(entries) - 1)]
    for i, entry in enumerate(entries[:-1]):
        parts = entry.split("\t")
        atlas_cg[i] = [int(p) for p in parts if p.strip()]

    with names_path.open("r") as fh:
        roi_names = fh.read().split("\n")

    logger.info("Atlas loaded: %d ROIs.", len(atlas_cg))
    return atlas_cg, roi_names


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_subject_data(root: Path, data_path: str, rat: str, group: str, map_group: str):
    """Load DWI, atlas, mask, gradient table and microstructural maps.

    Parameters
    ----------
    root:
        Project root directory.
    data_path:
        Relative path to the subject's data directory.
    rat:
        Subject identifier (e.g. ``"R01"``).
    group:
        Experimental group (e.g. ``"t1"``).
    map_group:
        Map filename prefix (e.g. ``"1"`` or ``"2"``).

    Returns
    -------
    dict
        All loaded arrays and gradient tables, keyed by descriptive names.
    """
    base = root / data_path.lstrip("/")
    #rat_prefix = f"/{rat}"

    paths = {
        "HARDI": base / f"{rat}_HARDI_MD_C_native_DWIs.nii",
        "bval":  base / f"{rat}_{group}_HARDI_MD_C_native_bval.txt",
        "bvec":  base / f"{rat}_{group}_HARDI_MD_C_native_bvec.txt",
        "mask":  base / f"{rat}_HARDI_mask_e.nii.gz",
        "atlas": base / f"{group}_atlas_s_gRL_awarped_{rat}.nii.gz",
        "AX":    base / f"maps_nifti/AX_{map_group}{rat}.nii",
        "FM":    base / f"maps_nifti/FM_{map_group}{rat}.nii",
        "FR":    base / f"maps_nifti/FR_{map_group}{rat}.nii",
        "MF":    base / f"maps_nifti/MF_{map_group}{rat}.nii",
        "FA":    base / f"maps_nifti/FA_{map_group}{rat}.nii",
    }

    for name, path in paths.items():
        if not path.exists():
            logger.warning("Expected file not found: %s → %s", name, path)

    data, affine, data_img = load_nifti(str(paths["HARDI"]), return_img=True)
    labels = load_nifti_data(str(paths["atlas"]))
    bvals = loadtxt(str(paths["bval"]), delimiter=" ")
    bvecs = loadtxt(str(paths["bvec"]), delimiter=" ")
    silvia_mask = load_nifti_data(str(paths["mask"]))

    AX = load_nifti_data(str(paths["AX"]))
    FM = load_nifti_data(str(paths["FM"]))
    FR = load_nifti_data(str(paths["FR"]))
    MF = load_nifti_data(str(paths["MF"]))
    FA = load_nifti_data(str(paths["FA"]))

    logger.info("Subject data loaded for rat %s, group %s.", rat, group)
    return dict(
        data=data, affine=affine, labels=labels,
        bvals=bvals, bvecs=bvecs, mask=silvia_mask,
        AX=AX, FM=FM, FR=FR, MF=MF, FA=FA,
    )


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def preprocess_dwi(data: np.ndarray, bvals: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Apply brain mask and patch2self denoising to DWI data.

    Parameters
    ----------
    data:
        4-D DWI array (x, y, z, volumes).
    bvals:
        b-value array.
    mask:
        3-D binary brain mask.

    Returns
    -------
    np.ndarray
        Denoised, masked DWI array.
    """
    n_vols = data.shape[3]
    masked = np.zeros_like(data)
    for vol in range(n_vols):
        masked[..., vol] = mask * data[..., vol]

    denoised = patch2self(
        masked, bvals, model="ols",
        shift_intensity=True, clip_negative_vals=False, b0_threshold=50
    )
    logger.info("DWI preprocessing complete (%d volumes).", n_vols)
    return denoised


# ---------------------------------------------------------------------------
# Tractography
# ---------------------------------------------------------------------------

def run_tractography(
    data: np.ndarray,
    bvals: np.ndarray,
    bvecs: np.ndarray,
    labels: np.ndarray,
    atlas: List[List[int]],
    mask: np.ndarray,
    affine: np.ndarray,
    fa_threshold: float = 0.15,
    seed_density: List[int] = None,
) -> List[np.ndarray]:
    """Run CSA-ODF tractography and return cleaned streamlines.

    Parameters
    ----------
    data:
        Preprocessed DWI array.
    bvals, bvecs:
        Gradient encoding tables.
    labels:
        Atlas label volume.
    atlas:
        Coarse-grain ROI mapping.
    mask:
        Tractography mask (ROI union).
    affine:
        Affine matrix.
    fa_threshold:
        FA stopping criterion (default 0.15).
    seed_density:
        Seeds per voxel per dimension (default ``[3, 3, 3]``).

    Returns
    -------
    List[np.ndarray]
        Cleaned streamlines.
    """
    if seed_density is None:
        seed_density = [3, 3, 3]

    # Build seed mask from white matter ROI (index 1)
    seed_mask = labels == atlas[1][0]
    for p in atlas[1]:
        seed_mask = seed_mask | (labels == p) | (labels == p + 1000)

    seeds = tracking_utils.seeds_from_mask(seed_mask, affine, density=seed_density)
    logger.info("Seeds generated: %d.", len(seeds))

    gtab = gradient_table(bvals, bvecs)
    csa_model = CsaOdfModel(gtab, sh_order_max=6)
    csa_peaks = peaks_from_model(
        csa_model, data, default_sphere,
        relative_peak_threshold=0.7,
        min_separation_angle=45,
        mask=mask,
    )
    logger.info("CSA-ODF peaks computed.")

    tensor_model = TensorModel(gtab)
    tensor_fit = tensor_model.fit(data)
    FA_vol = fractional_anisotropy(tensor_fit.evals)
    stopping = ThresholdStoppingCriterion(FA_vol, fa_threshold)

    raw_streamlines = Streamlines(
        LocalTracking(csa_peaks, stopping, seeds, affine=affine, step_size=0.1, maxlen=1000)
    )
    logger.info("Tractography done: %d raw streamlines.", len(raw_streamlines))

    cleaned = clean_streamlines(raw_streamlines)
    logger.info("Cleaned streamlines: %d.", len(cleaned))
    return cleaned, FA_vol


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    root: str,
    data_path: str,
    figures_path: str,
    group: str,
    rat: str,
    threshold: str = "0.0",
    plot: str = "0",
    map_group: str = "1",
    resolution: int = 512,
) -> int:
    """Full connectome matrix computation pipeline for a single subject.

    Parameters
    ----------
    root:
        Project root directory path.
    data_path:
        Relative path to raw DWI data directory.
    figures_path:
        Relative path for saving figures and intermediate results.
    group:
        Experimental group label (e.g. ``"t1"``).
    rat:
        Subject identifier (e.g. ``"R01"``).
    threshold:
        Fractional fibre inclusion threshold (string, e.g. ``"0.0"``).
    plot:
        ``"1"`` to enable 3-D figures; ``"0"`` to skip.
    map_group:
        Microstructural map prefix (``"1"`` = naïve, ``"2"`` = alcohol).
    resolution:
        Figure resolution in pixels.

    Returns
    -------
    int
        0 on success.
    """
    t_start = time.time()
    root_path = Path(root)
    out_path = root_path / figures_path.lstrip("/")
    out_path.mkdir(parents=True, exist_ok=True)

    logger.info("=== Pipeline start: rat=%s, group=%s ===", rat, group)

    # -- Atlas ----------------------------------------------------------------
    atlas_cg, roi_names = load_atlas(root_path)

    # -- Data -----------------------------------------------------------------
    subject = load_subject_data(root_path, data_path, rat, group, map_group)

    # Build ROI mask
    #roi_mask = labels = subject["labels"]
    labels = subject["labels"]
    atlas_mask = labels == atlas_cg[1][0]
    for roi_idx in range(1, 79):
        for p in atlas_cg[roi_idx]:
            atlas_mask = atlas_mask | (labels == p) | (labels == p + 1000)

    # -- Pre-processing -------------------------------------------------------
    data_proc = preprocess_dwi(subject["data"], subject["bvals"], subject["mask"])
    t1_data = data_proc[..., 0]

    # -- Tractography ---------------------------------------------------------
    streamlines, FA_vol = run_tractography(
        data_proc, subject["bvals"], subject["bvecs"],
        subject["labels"], atlas_cg, atlas_mask, subject["affine"]
    )

    # -- Coronal plots --------------------------------------------------------
    #coronal_dir = str(out_path)
    plot_coronal_slices(
        build_velocity_volume(subject["mask"], subject["FM"], subject["FR"], subject["AX"]),
        0, 12.5,
        str(out_path / f"coronal_{rat}_V.png"),
    )
    #for name, vol in [("AX", subject["AX"]), ("FM", subject["FM"]),
    #                  ("FR", subject["FR"]), ("FA", subject["FA"])]:
    #    plot_coronal_slices(vol, 0, vol.max() / 2,
    #                        str(out_path / f"coronal_{rat}_{name}.png"))

    # Save FA tracking mask figure
    sli = FA_vol.shape[2] // 2
    fig, (ax1, ax2) = plt.subplots(1, 2)
    ax1.axis("off"); 
    ax1.imshow(FA_vol[:, :, sli].T, cmap="gray", origin="lower")
    ax2.axis("off"); 
    ax2.imshow((FA_vol[:, :, sli] > 0.15).T, cmap="gray", origin="lower")
    fig.savefig(str(out_path / f"FA_tracking_mask_{rat}.png"))
    plt.close(fig)

    # -- Connectivity matrices ------------------------------------------------
    N_NODES = 79
    mat_size = 2 * N_NODES

    W = np.zeros((mat_size, mat_size))
    D = np.zeros((mat_size, mat_size))
    V = np.zeros((mat_size, mat_size))

    roi_i = [8, 12, 70]
    roi_j = [29, 91]

    for i in roi_i:
        for j in roi_j:
            if j <= i:
                continue

            logger.info("Processing ROI pair (%d, %d).", i, j)

            W[i, j], D[i, j], bundle = get_roi_streamlines(
                i, j, N_NODES, streamlines, subject["labels"], atlas_cg, subject["affine"]
            )

            if W[i, j] > 0:
                vel_data, ax_d, fm_d, fr_d, fa_d = compute_velocities(
                    bundle, subject["affine"],
                    subject["AX"], subject["FM"], subject["FR"], subject["FA"]
                )

                all_vels = [v for fiber in vel_data for v in fiber]
                V[i, j] = float(np.median(all_vels)) if all_vels else 0.0

                # Save dictionaries
                save_dict({(i, j): bundle},
                          str(out_path / f"Streamlines_{rat}_ij_{i}-{j}.dat"))
                save_dict({(i, j): vel_data},
                          str(out_path / f"Velocities_{rat}_ij_{i}-{j}.dat"))
                save_dict({(i, j): ax_d},
                          str(out_path / f"AX_{rat}_ij_{i}-{j}.dat"))
                save_dict({(i, j): fm_d},
                          str(out_path / f"FM_{rat}_ij_{i}-{j}.dat"))
                save_dict({(i, j): fr_d},
                          str(out_path / f"FR_{rat}_ij_{i}-{j}.dat"))
                save_dict({(i, j): fa_d},
                          str(out_path / f"FA_{rat}_ij_{i}-{j}.dat"))

                if int(plot):
                    plot_streamlines_3d(
                        i, j, bundle, N_NODES, 40, 20,
                        str(out_path / f"Streamlines_{rat}_ij_{i}-{j}.png"),
                        subject["labels"], atlas_cg, subject["affine"],
                        t1_data, resolution,
                    )
            else:
                logger.warning("W[%d,%d] = 0 — no dictionaries saved.", i, j)

    # Save matrices
    for name, mat in [("W", W), ("D", D), ("V", V)]:
        save_matrix_as_text(mat, str(out_path / f"{name}_matrix_{rat}.txt"))

    elapsed = (time.time() - t_start) / 60.0
    logger.info("Pipeline complete in %.2f min.", elapsed)
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute W/D/V connectivity matrices for one subject."
    )
    parser.add_argument("--root",         required=True, help="Project root path")
    parser.add_argument("--data-path",    required=True, help="Relative data path")
    parser.add_argument("--figures-path", required=True, help="Relative output path")
    parser.add_argument("--group",        required=True, help="Group label (e.g. t1)")
    parser.add_argument("--rat",          required=True, help="Subject ID (e.g. R01)")
    parser.add_argument("--threshold",    default="0.0", help="Fibre inclusion threshold")
    parser.add_argument("--plot",         default="0",   help="Enable 3D figures (1/0)")
    parser.add_argument("--map-group",    default="1",   help="Map group prefix (1 or 2)")
    parser.add_argument("--resolution",   default=512,   type=int)
    parser.add_argument("--log-level",    default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    sys.exit(
        run_pipeline(
            args.root, args.data_path, args.figures_path,
            args.group, args.rat, args.threshold,
            args.plot, args.map_group, args.resolution,
        )
    )
