# Installation Guide

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Ubuntu 20.04 / macOS 12 / WSL2 | Ubuntu 22.04 LTS |
| Python | 3.9 | 3.10 |
| RAM | 8 GB | 16 GB |
| Disk | 20 GB free | 50 GB free |
| GPU | Not required | — |

---

## Option A — Conda (Recommended)

Conda handles both Python and native library dependencies cleanly.

### 1. Install Miniconda

```bash
# Linux / WSL2
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Or follow the [official instructions](https://docs.conda.io/en/latest/miniconda.html) for your OS.

### 2. Create the environment

```bash
conda env create -f config/environment.yml
conda activate rat-conn_env
```

### 3. Verify

```bash
python3 validations/validate_environment.py --root $(pwd)
```

---

## Option B — pip / venv

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install \
    numpy scipy matplotlib seaborn \
    dipy nibabel scikit-learn fury
```

> **Note:** `fury` requires VTK and may need system libraries on Linux:
> ```bash
> sudo apt-get install -y libvtk9-dev
> ```

---

## Option C — Docker

No local installation required beyond Docker itself. See [Docker.md](Docker.md).

---

## Post-Installation: Data Preparation

Place your raw subject data under `data/raw/` following this layout:

```
data/raw/
├── atlas_cg_3d5_list.txt
├── atlas_cg_3d5_names.txt
├── t1/
│   └── R01/
│       ├── R01_HARDI_MD_C_native_DWIs.nii
│       ├── R01_t1_HARDI_MD_C_native_bval.txt
│       ├── R01_t1_HARDI_MD_C_native_bvec.txt
│       ├── R01_HARDI_mask_e.nii.gz
│       ├── /t1_atlas_s_gRL_awarped_R01.nii.gz
│       └── maps_nifti/
│           ├── AX_1R01.nii
│           ├── FM_1R01.nii
│           ├── FR_1R01.nii
│           ├── MF_1R01.nii
│           └── FA_1R01.nii
└── t2/
    └── R01/
        └── ...
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: dipy` | Activate the conda environment: `conda activate rat-conn_env` |
| `fury` import warning | Install VTK system library or set `save_3d_figures: false` in `config/connectome_config.json` |
| Memory error during tractography | Reduce `seed_density` in `config/connectome_config.json` |
| Slow tractography on cluster | Use the SLURM lines in `scripts/batch_connectome_matrix.sh` |
