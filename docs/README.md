# Rat Structural Connectome Pipeline

A Python + Bash pipeline for computing structural brain connectivity matrices from diffusion-weighted MRI data in rats. The pipeline extracts per-subject W (fibre count), D (fibre length), V (axon velocity), τ (signal delay), and FA (fractional anisotropy) matrices, then performs group-level statistical comparisons between naïve and alcohol-exposed animals.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Pipeline Stages](#pipeline-stages)
5. [Configuration](#configuration)
6. [Running Tests](#running-tests)
7. [Docker](#docker)
8. [Contributing](#contributing)
9. [License](#license)

---

## Overview

The pipeline consists of three sequential stages:

| Stage | Script | What it does |
|---|---|---|
| 1. Connectome matrices | `connectome_matrix_pipeline.py` | Tractography → W, D, V matrices per subject |
| 2. Tau fitting | `gaussian_tau_pipeline.py` | Per-fibre τ, FA matrices per subject |
| 3. Group statistics | `structural_connectivity_analysis.py` | Group masks, heatmaps, KS/MWU/Cohen's d |

---

## Project Structure

```
rat-connectome/
├── source/                     # Python source modules
│   ├── streamline_utils.py
│   ├── connectome_matrix_pipeline.py
│   ├── gaussian_tau_pipeline.py
│   ├── statistics_utils.py
│   ├── structural_connectivity_analysis.py
│   └── logging_config.py
├── scripts/                    # Bash runner scripts
│   ├── run_connectome_matrix.sh
│   ├── batch_connectome_matrix.sh
│   ├── run_gaussian_fitting.sh
│   ├── batch_gaussian_fitting.sh
│   └── run_statistics_analysis.sh
├── config/
│   ├── connectome_config.json
│   ├── subjects.json
│   └── environment.yml
├── data/
│   ├── raw/                    # Input NIfTI, bval/bvec, atlas files
│   └── processed/              # Intermediate pre-processed files
├── results/                    # Pipeline outputs (matrices, figures)
├── logs/                       # Auto-generated run logs
├── validations/
│   ├── validate_environment.py
│   └── validate_matrices.py
├── tests/
│   ├── test_streamline_utils.py
│   └── test_gaussian_tau_pipeline.py
├── docs/
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── installation.md
│   ├── api.md
│   ├── GitHub.md
│   └── Docker.md
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── pyproject.toml
```

---

## Quick Start

See [docs/QUICKSTART.md](QUICKSTART.md) for full instructions including Conda and Docker options.

**TL;DR:**

```bash
conda env create -f config/environment.yml
conda activate rat-conn_env

# Validate setup
python3 validations/validate_environment.py --root /workspace/connectome

# Stage 1 – one subject
bash scripts/run_connectome_matrix.sh \
    /workspace/connectome /data/raw/t1/R01 \
    /results/t1/FA_RN_SI_v0-1_th-0/R01 t1 R01 0.0 0 1

# Stage 2 – Gaussian/tau fitting
bash scripts/run_gaussian_fitting.sh \
    /workspace/connectome \
    /results/t1/FA_RN_SI_v0-1_th-0 \
    /results/t1/FA_RN_SI_v0-1_th-0.0/filter_kick_out \
    0.0 R01

# Stage 3 – Group statistics
bash scripts/run_statistics_analysis.sh /workspace/connectome
```

---

## Pipeline Stages

### Stage 1: Connectome Matrices

Runs CSA-ODF tractography on each subject's DWI data, targets streamlines to all ROI pairs, computes per-voxel axon velocities, and saves W/D/V matrices plus streamline/velocity dictionaries.

**Inputs:** NIfTI DWI, bval/bvec, atlas, microstructural maps (AX, FM, FR, FA).  
**Outputs:** `W_matrix_R*.txt`, `D_matrix_R*.txt`, `V_matrix_R*.txt`, `*.dat` dictionaries.

### Stage 2: Tau Fitting

Loads per-pair streamline and velocity dictionaries, computes fibre arc length and median velocity, filters slow voxels, and saves w/d/v/tau/fa matrices.

**Inputs:** `.dat` dictionaries from Stage 1.  
**Outputs:** `th-0.0_R*_{w,d,v,tau,fa}.txt` matrices.

### Stage 3: Group Statistics

Builds group connectivity masks, applies them to both groups' matrices, generates heatmaps and histograms, and runs KS, Mann–Whitney U, and Cohen's d comparisons.

**Inputs:** per-subject matrices from Stage 2.  
**Outputs:** PNG figures, per-rat and ensemble statistical summaries.

---

## Configuration

Edit `config/connectome_config.json` to change tractography parameters, ROI size, or output paths.  
Edit `config/subjects.json` to add or exclude subjects.

---

## Running Tests

```bash
conda activate rat-conn_env
python3 -m pytest tests/ -v
```

---

## Docker

```bash
docker compose up --build connectome
```

See [docs/Docker.md](Docker.md) for full instructions.

---

## Contributing

See [docs/GitHub.md](GitHub.md) for branching strategy, commit conventions, and PR guidelines.

---

## License

MIT — see `LICENSE`.
