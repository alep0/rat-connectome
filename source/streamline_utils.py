"""
streamline_utils.py
====================
Utility functions for streamline processing, velocity computation,
ROI targeting, and matrix/dictionary I/O.

Refactored from: Streamlines_functions_v1.py
"""

import logging
import pickle
#from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from dipy.tracking import utils
from dipy.tracking._utils import _mapping_to_voxel, _to_voxel_coordinates
from dipy.tracking.streamline import Streamlines
from dipy.viz import actor, colormap, has_fury, window

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Streamline cleaning
# ---------------------------------------------------------------------------

def clean_streamlines(raw_streamlines) -> List[np.ndarray]:
    """Remove degenerate streamlines (single-point segments).

    Parameters
    ----------
    raw_streamlines:
        A Streamlines object whose ``_lengths`` / ``_data`` / ``_offsets``
        attributes describe each individual tract.

    Returns
    -------
    List[np.ndarray]
        List of (N, 3) arrays, one per valid streamline.
    """
    cleaned: List[np.ndarray] = []
    for i in range(len(raw_streamlines._lengths)):
        length = raw_streamlines._lengths[i]
        if length > 1:
            segment = np.zeros((length, 3))
            for j in range(length):
                for k in range(3):
                    segment[j, k] = raw_streamlines._data[
                        raw_streamlines._offsets[i] + j, k
                    ]
            cleaned.append(segment)

    logger.debug("Cleaned %d / %d streamlines kept.", len(cleaned), len(raw_streamlines._lengths))
    return cleaned


# ---------------------------------------------------------------------------
# Streamline cutting
# ---------------------------------------------------------------------------

def cut_streamlines(
    streamlines: List[np.ndarray],
    roi_p: List[int],
    roi_q: List[int],
    affine: np.ndarray,
    labels: np.ndarray,
) -> List[np.ndarray]:
    """Trim each streamline so it spans exactly from ROI *p* to ROI *q*.

    Parameters
    ----------
    streamlines:
        List of (N, 3) coordinate arrays.
    roi_p, roi_q:
        Label indices for the two endpoint ROIs.
    affine:
        Affine transformation for voxel mapping.
    labels:
        3-D integer array of atlas labels.

    Returns
    -------
    List[np.ndarray]
        Trimmed streamlines.
    """
    lin_T, offset = _mapping_to_voxel(affine)
    result: List[np.ndarray] = []

    for streamline in streamlines:
        voxel_indices = _to_voxel_coordinates(streamline, lin_T, offset)
        ix, jx, kx = voxel_indices.T
        state = labels[ix, jx, kx]

        flag = start_idx = end_idx = active_roi = 0

        for idx, label in enumerate(state):
            if flag == 2:
                break

            if flag == 1:
                if active_roi == min(roi_p) and label in roi_q:
                    end_idx = idx
                    flag = 2
                    break
                if active_roi == min(roi_q) and label in roi_p:
                    end_idx = idx
                    flag = 2
                    break

            if flag == 0:
                if label in roi_p:
                    flag = 1
                    start_idx = idx
                    active_roi = min(roi_p)
                elif label in roi_q:
                    flag = 1
                    start_idx = idx
                    active_roi = min(roi_q)

        result.append(streamline[start_idx:end_idx])

    logger.debug("cut_streamlines: returned %d segments.", len(result))
    return result


# ---------------------------------------------------------------------------
# ROI pair targeting
# ---------------------------------------------------------------------------

def get_roi_streamlines(
    i: int,
    j: int,
    n_nodes: int,
    streamlines: List[np.ndarray],
    labels: np.ndarray,
    atlas: List[List[int]],
    affine: np.ndarray,
) -> Tuple[int, float, List[np.ndarray]]:
    """Return streamlines connecting ROI *i* and ROI *j*, plus W and D metrics.

    Parameters
    ----------
    i, j:
        ROI indices (supports hemispheric offset via ``i >= n_nodes``).
    n_nodes:
        Number of ROIs per hemisphere.
    streamlines:
        Full tractogram.
    labels:
        Atlas label volume.
    atlas:
        Coarse-grain ROI label mapping.
    affine:
        Affine matrix.

    Returns
    -------
    Tuple[int, float, List[np.ndarray]]
        ``(W, D, bundle)`` — fibre count, median length, trimmed fibres.
    """

    def _build_roi_mask(index: int):
        labels_list: List[int] = []
        if index < n_nodes:
            #roi_labels = atlas[index]
            roi_mask = labels == atlas[index][0]
            for p in atlas[index]:
                roi_mask = roi_mask | (labels == p)
            labels_list = atlas[index]
        else:
            roi_idx = index % n_nodes
            roi_mask = labels == atlas[roi_idx][0] + 1000
            for p in atlas[roi_idx]:
                roi_mask = roi_mask | (labels == p + 1000)
                labels_list.append(p + 1000)
        return roi_mask, labels_list

    roi_mask_i, labels_i = _build_roi_mask(i)
    roi_mask_j, labels_j = _build_roi_mask(j)

    cc_streamlines = Streamlines(utils.target(streamlines, affine, roi_mask_i))
    cc_streamlines = Streamlines(utils.target(cc_streamlines, affine, roi_mask_j))

    logger.info("ROI pair (%d, %d): %d streamlines found.", i, j, len(cc_streamlines))

    W = len(cc_streamlines)
    if W > 0:
        bundle = cut_streamlines(
            clean_streamlines(cc_streamlines), labels_i, labels_j, affine, labels
        )
        lengths = [len(s) for s in bundle]
        D = float(np.median(lengths))
    else:
        bundle = []
        D = 0.0

    return W, D, bundle


# ---------------------------------------------------------------------------
# Velocity computation
# ---------------------------------------------------------------------------

def compute_velocities(
    streamlines: List[np.ndarray],
    affine: np.ndarray,
    AX: np.ndarray,
    FM: np.ndarray,
    FR: np.ndarray,
    FA: np.ndarray,
) -> Tuple[List, List, List, List, List]:
    """Compute per-voxel axon velocities and microstructural maps along streamlines.

    The velocity formula is:
        v = 6 * AX * sqrt( -log( 1 / sqrt( 1 + FM / ((1 - FM) * FR) ) ) )

    Parameters
    ----------
    streamlines:
        List of (N, 3) coordinate arrays.
    affine:
        Voxel-to-world affine.
    AX, FM, FR, FA:
        3-D microstructural parameter volumes.

    Returns
    -------
    Tuple of five lists: velocities, AX values, FM values, FR values, FA values
        — one entry per streamline, each entry is an array of per-voxel values.
    """
    lin_T, offset = _mapping_to_voxel(affine)

    velocities, ax_vals, fm_vals, fr_vals, fa_vals = [], [], [], [], []

    for streamline in streamlines:
        voxels = _to_voxel_coordinates(streamline, lin_T, offset)
        ii, jj, kk = voxels.T

        s_ax = AX[ii, jj, kk]
        s_fm = FM[ii, jj, kk]
        s_fr = FR[ii, jj, kk]
        s_fa = FA[ii, jj, kk]

        vel = np.zeros(len(s_ax))
        for o in range(len(s_ax)):
            denom = (1.0 - s_fm[o]) * s_fr[o]
            if denom > 0:
                g = 1.0 / np.sqrt(1.0 + s_fm[o] / denom)
                log_val = -1.0 * np.log(g) if g > 0 else 0.0
                vel[o] = 6.0 * s_ax[o] * np.sqrt(max(log_val, 0.0))

        velocities.append(vel)
        ax_vals.append(s_ax)
        fm_vals.append(s_fm)
        fr_vals.append(s_fr)
        fa_vals.append(s_fa)

    logger.debug("compute_velocities: processed %d streamlines.", len(streamlines))
    return velocities, ax_vals, fm_vals, fr_vals, fa_vals


def build_velocity_volume(
    mask: np.ndarray,
    FM: np.ndarray,
    FR: np.ndarray,
    AX: np.ndarray,
) -> np.ndarray:
    """Build a 3-D velocity map from microstructural parameter volumes.

    Parameters
    ----------
    mask:
        Binary brain mask (1 inside brain, 0 outside).
    FM, FR, AX:
        Microstructural parameter volumes.

    Returns
    -------
    np.ndarray
        3-D velocity volume; voxels outside the mask are set to ``-1``.
    """
    velocity_vol = np.full(mask.shape, -1.0)
    for i in range(mask.shape[0]):
        for j in range(mask.shape[1]):
            for k in range(mask.shape[2]):
                if mask[i, j, k] == 1:
                    denom = (1.0 - FM[i, j, k]) * FR[i, j, k]
                    if denom > 0:
                        g = 1.0 / np.sqrt(1.0 + FM[i, j, k] / denom)
                        velocity_vol[i, j, k] = 6.0 * AX[i, j, k] * np.sqrt(
                            max(-np.log(g), 0.0)
                        )
    logger.debug("build_velocity_volume: done.")
    return velocity_vol


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def plot_coronal_slices(
    volume: np.ndarray,
    vmin: float,
    vmax: float,
    output_path: str,
) -> None:
    """Save a 4×4 coronal slice montage of *volume*.

    Parameters
    ----------
    volume:
        3-D array to visualise.
    vmin, vmax:
        Colour-scale limits.
    output_path:
        Destination file path (PNG).
    """
    fig, axes = plt.subplots(4, 4, figsize=(12, 12))
    for idx, ax in enumerate(axes.flat):
        ax.axis("off")
        im = ax.imshow(
            volume[:, :, idx].T, cmap="gray", vmin=vmin, vmax=vmax, origin="lower"
        )
        plt.colorbar(im, ax=ax)

    plt.savefig(output_path, dpi=2048)
    plt.close(fig)
    logger.info("Coronal plot saved → %s", output_path)


def plot_streamlines_3d(
    i: int,
    j: int,
    streamlines: List[np.ndarray],
    n_nodes: int,
    azimuth: float,
    elevation: float,
    output_path: str,
    labels: np.ndarray,
    atlas: List[List[int]],
    affine: np.ndarray,
    t1_data: np.ndarray,
    resolution: int = 512,
) -> None:
    """Render and save a 3-D streamline figure for ROI pair (i, j).

    Parameters
    ----------
    i, j:
        ROI indices.
    streamlines:
        Streamlines connecting ROI pair.
    n_nodes:
        Number of ROIs per hemisphere.
    azimuth, elevation:
        Camera angles in degrees.
    output_path:
        Destination PNG path.
    labels:
        Atlas volume.
    atlas:
        Coarse-grain atlas mapping.
    affine:
        Affine matrix.
    t1_data:
        Anatomical background image.
    resolution:
        Image size (pixels).
    """
    if not has_fury:
        logger.warning("Fury not available; skipping 3-D streamline plot.")
        return

    def _roi_mask(index: int) -> np.ndarray:
        if index < n_nodes:
            mask = labels == atlas[index][0]
            for p in atlas[index]:
                mask = mask | (labels == p)
        else:
            ri = index % n_nodes
            mask = labels == atlas[ri][0] + 1000
            for p in atlas[ri]:
                mask = mask | (labels == p + 1000)
        return mask

    nst = Streamlines(streamlines)
    scene = window.Scene()

    scene.add(actor.line(nst, colors=colormap.line_colors(nst)))
    scene.add(
        actor.contour_from_roi(_roi_mask(i), affine=affine, color=(1.0, 1.0, 1.0), opacity=0.3)
    )
    scene.add(
        actor.contour_from_roi(_roi_mask(j), affine=affine, color=(1.0, 1.0, 0.0), opacity=0.3)
    )

    vol_actor = actor.slicer(t1_data, affine=affine)
    vol_actor.display(x=25)
    scene.add(vol_actor)
    vol2 = vol_actor.copy()
    vol2.display(z=1)
    scene.add(vol2)
    vol3 = vol_actor.copy()
    vol3.display(y=40)
    scene.add(vol3)

    scene.azimuth(azimuth)
    scene.elevation(elevation)

    window.record(scene=scene, n_frames=1, out_path=output_path, size=(resolution, resolution))
    logger.info("3-D streamline figure saved → %s", output_path)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_dict(data: Dict, filepath: str) -> None:
    """Serialise *data* to a pickle file.

    Parameters
    ----------
    data:
        Dictionary to serialise.
    filepath:
        Destination path (will be created if parent exists).
    """
    with open(filepath, "wb") as fh:
        pickle.dump(data, fh)
    logger.info("Dictionary saved → %s", filepath)


def load_dict(filepath: str) -> Dict:
    """Deserialise a pickle file, returning an empty dict on failure.

    Parameters
    ----------
    filepath:
        Source path.

    Returns
    -------
    Dict
        Loaded dictionary, or ``{}`` if the file is missing / corrupt.
    """
    try:
        with open(filepath, "rb") as fh:
            return pickle.load(fh)
    except (OSError, IOError, pickle.UnpicklingError) as exc:
        logger.warning("Could not load dict from %s: %s", filepath, exc)
        return {}


def save_matrix_as_text(matrix: np.ndarray, filepath: str) -> None:
    """Write a 2-D numpy array to a whitespace-delimited text file.

    Parameters
    ----------
    matrix:
        2-D array to write.
    filepath:
        Destination path.
    """
    try:
        with open(filepath, "w") as fh:
            for row in matrix:
                fh.write(" ".join(map(str, row)) + "\n")
        logger.info("Matrix saved → %s", filepath)
    except FileNotFoundError as exc:
        logger.error("save_matrix_as_text failed for %s: %s", filepath, exc)
