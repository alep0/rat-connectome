# API Reference

All public functions follow Google-style docstrings. Below is a structured reference grouped by module.

---

## `streamline_utils`

Core utilities shared by all pipeline stages.

### `clean_streamlines(raw_streamlines) → List[ndarray]`
Remove degenerate (single-point) streamlines from a Streamlines object.

### `cut_streamlines(streamlines, roi_p, roi_q, affine, labels) → List[ndarray]`
Trim each streamline so it spans exactly from ROI `p` to ROI `q`.

### `get_roi_streamlines(i, j, n_nodes, streamlines, labels, atlas, affine) → (W, D, bundle)`
Return streamlines connecting ROI `i` and ROI `j`, plus fibre count W and median length D.

### `compute_velocities(streamlines, affine, AX, FM, FR, FA) → (vel, ax, fm, fr, fa)`
Compute per-voxel axon velocities along streamlines using the formula:

```
v = 6 * AX * sqrt( -log( 1 / sqrt( 1 + FM / ((1 - FM) * FR) ) ) )
```

### `build_velocity_volume(mask, FM, FR, AX) → ndarray`
Compute a 3-D velocity map from microstructural volumes.

### `plot_coronal_slices(volume, vmin, vmax, output_path)`
Save a 4×4 coronal slice montage.

### `plot_streamlines_3d(i, j, streamlines, ..., output_path)`
Render and save a 3-D streamline figure for a ROI pair (requires Fury).

### `save_dict(data, filepath)` / `load_dict(filepath) → dict`
Pickle-based dictionary serialisation. `load_dict` returns `{}` on missing file.

### `save_matrix_as_text(matrix, filepath)`
Write a 2-D numpy array to a whitespace-delimited text file.

---

## `connectome_matrix_pipeline`

### `load_atlas(root) → (atlas_cg, roi_names)`
Load coarse-grain ROI label mapping and ROI names from text files.

### `load_subject_data(root, data_path, rat, group, map_group) → dict`
Load all NIfTI images, bval/bvec, and microstructural maps for one subject.

### `preprocess_dwi(data, bvals, mask) → ndarray`
Apply brain mask and patch2self denoising.

### `run_tractography(data, bvals, bvecs, labels, atlas, mask, affine, ...) → (streamlines, FA_vol)`
Run CSA-ODF tractography and return cleaned streamlines.

### `run_pipeline(root, data_path, figures_path, group, rat, threshold, plot, map_group, resolution) → int`
**Main entry point.** Runs the full tractography → matrix → dictionary pipeline for one subject.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| root | str | Project root path |
| data_path | str | Relative path to subject DWI data |
| figures_path | str | Relative path for outputs |
| group | str | Group label (`"t1"` or `"t2"`) |
| rat | str | Subject ID (`"R01"`, ...) |
| threshold | str | Fibre filter (e.g. `"0.0"`) |
| plot | str | `"1"` = save 3-D figures |
| map_group | str | `"1"` = naïve, `"2"` = alcohol |
| resolution | int | Figure resolution in pixels |

**Returns:** `0` on success.

---

## `gaussian_tau_pipeline`

### `compute_tau_per_roi_pair(streamlines, velocities, ax_data, fm_data, fr_data, fa_data, threshold, histogram_path) → (records, dists, vels, taus, fas)`
Compute τ, d, v, and FA for all fibres connecting one ROI pair.

Each element of `records` is: `[tau, d, v, ax_median, fm_median, fr_median, fa_median]`.

### `run_gaussian_fitting(root, data_dir, output_dir, threshold, rat) → int`
**Main entry point.** Loads per-pair dictionaries and produces w/d/v/tau/fa matrices.

---

## `statistics_utils`

### `cohens_d(x, y) → float`
Compute Cohen's d using pooled standard deviation.

### `analyze_and_plot(data1, data2, label1, label2, output_dir, variable_name) → dict`
Run KS test, Mann–Whitney U test, and Cohen's d; save CDF and boxplot figures.

**Returns:** `{"ks_stat", "ks_p", "mw_stat", "mw_p", "cohens_d"}`

---

## `structural_connectivity_analysis`

### `load_matrix(directory, filename) → ndarray`
Load a whitespace-delimited connectivity matrix.

### `matrix_to_vector(matrix, threshold) → List[float]`
Extract upper-triangle values above `threshold`.

### `apply_mask(matrix, mask) → ndarray`
Element-wise multiply upper-triangle of `matrix` by `mask`.

### `compute_group_mask(rats, data_path, fibre_threshold, rat_threshold) → ndarray`
Build a binary group connectivity mask (connection present if ≥ `rat_threshold` subjects have it).

### `plot_connectivity_matrix(matrix, output_dir, name, color_limit, mode, saturation)`
Save a seaborn heatmap of a connectivity matrix.

### `plot_histogram(matrix, output_dir, name, scale, x_limit)`
Save a histogram of upper-triangle values.

### `run_group_analysis(root, output_name, model_1, group_1, model_2, group_2, variable, color_limit, log_scale, scale_factor)`
**Main entry point.** Full group-level comparison for one variable.

---

## `logging_config`

### `setup_logging(log_dir, level, script_name) → Logger`
Configure the root logger with file + console handlers.

---

## CLI Entry Points

Every module can also be called directly:

```bash
python3 source/connectome_matrix_pipeline.py --help
python3 source/gaussian_tau_pipeline.py --help
python3 source/structural_connectivity_analysis.py --help
python3 source/statistics_utils.py --help
python3 validations/validate_environment.py --help
python3 validations/validate_matrices.py --help
```
