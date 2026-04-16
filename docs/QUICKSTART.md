# Quickstart Guide

This guide gets you from a fresh clone to a complete pipeline run in the shortest possible path.

---

## Prerequisites

- Git
- Either: Conda (Miniconda/Anaconda) **or** Docker

---

## 1. Clone the Repository

```bash
git clone https://github.com/alep0/rat-connectome.git
cd rat-connectome
```

---

## 2. Set Up the Environment

### Option A — Conda

```bash
conda env create -f config/environment.yml
conda activate rat-conn_env
```

### Option B — Docker

```bash
docker compose build connectome
```

No further setup needed; skip to Step 4 for Docker runs.

---

## 3. Validate the Environment (Conda only)

```bash
python3 validations/validate_environment.py --root $(pwd)
```

Expected output:
```
[OK] Python version: 3.10
[OK] Required packages: numpy, scipy, matplotlib, dipy, ...
[OK] Project directories
[OK] Config files
[OK] Source modules
All required checks PASSED.
```

---

## 4. Prepare Data

Place your subject data under `data/raw/` as described in [installation.md](installation.md).

---

## 5. Configure

Review and edit if needed:

```bash
nano config/connectome_config.json   # tractography / output settings
nano config/subjects.json            # subject list
```

---

## 6. Run Stage 1 — Connectome Matrices (one subject)

**Conda:**
```bash
conda activate rat-conn_env

bash scripts/run_connectome_matrix.sh \
    $(pwd) \
    /data/raw/t1/R01 \
    /results/t1/FA_RN_SI_v0-1_th-0/R01 \
    t1 R01 0.0 0 1
```

**Docker:**
```bash
docker compose run --rm connectome \
    conda run --no-capture-output -n rat-conn_env \
    bash /workspace/connectome/scripts/run_connectome_matrix.sh \
    /workspace/connectome \
    /data/raw/t1/R04 \
    /results/t1/FA_RN_SI_v0-1_th-0/R04 \
    t1 R04 0.0 0 1
```

**All subjects:**
```bash
bash scripts/batch_connectome_matrix.sh $(pwd) "R02 R03" 1 2 0 # edit RATS variable inside first
```

---

## 7. Run Stage 2 — Tau / Gaussian Fitting

```bash
bash scripts/run_gaussian_fitting.sh \
    $(pwd) \
    /results/t1/FA_RN_SI_v0-1_th-0 \
    /results/t1/FA_RN_SI_v0-1_th-0.0/filter_kick_out/R01 \
    0.0 R01
```

All subjects:
```bash
bash scripts/batch_gaussian_fitting.sh $(pwd) "R02 R03" 1 2 0 
```

---

## 8. Run Stage 3 — Group Statistics

```bash
bash scripts/run_statistics_analysis.sh $(pwd)
```

Results (PNG figures + stats) appear in `results/`.

---

## 9. Validate Outputs

```bash
python3 validations/validate_matrices.py \
    --root $(pwd) \
    --results-dir results/t1/FA_RN_SI_v0-1_th-0.0/filter_kick_out \
    --rat R01 \
    --threshold 0.0
```

---

## 10. Run Tests

```bash
python3 -m pytest tests/ -v
```

---

## Cluster (SLURM) Usage

Edit the SLURM lines in each batch script, then submit:

```bash
bash scripts/batch_connectome_matrix.sh   # uses `run` wrapper if uncommented
bash scripts/batch_gaussian_fitting.sh
```

Download results from cluster:

```bash
ssh user@cluster "cd /path/to/results && tar --exclude='*.png' -cvf - ." \
    | tar -xf - -C ./results/
```

---

## File Naming Conventions

| File | Description |
|---|---|
| `th-0.0_R01_w.txt` | W (fibre count) matrix — rat R01, threshold 0.0 |
| `th-0.0_R01_tau.txt` | τ (delay) matrix |
| `Streamlines_R01_ij_8-29.dat` | Streamline dictionary — ROI pair (8, 29) |
| `Velocities_R01_ij_8-29.dat` | Velocity dictionary — ROI pair (8, 29) |
