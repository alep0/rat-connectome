# Docker Guide

## Overview

The project ships with a `Dockerfile` and `docker-compose.yml` so the entire pipeline can run in an isolated, reproducible environment with no local Python installation required.

---

## Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) v2

---

## Build

```bash
docker compose build connectome
```

This creates the `rat-connectome:latest` image (~2 GB) with all dependencies pre-installed.

---

## Run the Full Pipeline

```bash
# Stage 1 — Connectome matrices (one subject)
docker compose run --rm connectome \
    bash /workspace/connectome/scripts/run_connectome_matrix.sh \
    /workspace/connectome \
    /data/raw/t1/R01 \
    /results/t1/FA_RN_SI_v0-1_th-0/R01 \
    t1 R01 0.0 0 1

# Stage 2 — Tau fitting
docker compose run --rm connectome \
    bash /workspace/connectome/scripts/run_gaussian_fitting.sh \
    /workspace/connectome \
    /results/t1/FA_RN_SI_v0-1_th-0 \
    /results/t1/FA_RN_SI_v0-1_th-0.0/filter_kick_out \
    0.0 R01

# Stage 3 — Statistics
docker compose run --rm connectome \
    bash /workspace/connectome/scripts/run_statistics_analysis.sh \
    /workspace/connectome
```

---

## Interactive Shell

```bash
docker compose run --rm connectome bash
```

Inside the container:
```bash
conda activate conn_env
python3 validations/validate_environment.py --root /workspace/connectome
```

---

## Volume Mounts

The `docker-compose.yml` mounts:

| Host path | Container path | Purpose |
|---|---|---|
| `./data` | `/workspace/connectome/data` | Input NIfTI / atlas files |
| `./results` | `/workspace/connectome/results` | Pipeline outputs |
| `./logs` | `/workspace/connectome/logs` | Log files |
| `./config` | `/workspace/connectome/config` | Configuration files |

Data written to `/workspace/connectome/results` inside the container automatically appears in `./results` on the host.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Python logging verbosity |
| `CONNECTOME_ROOT` | `/workspace/connectome` | Project root inside container |

Set in `docker-compose.yml` or override at runtime:
```bash
docker compose run -e LOG_LEVEL=DEBUG --rm connectome bash scripts/run_statistics_analysis.sh /workspace/connectome
```

---

## Rebuilding After Code Changes

Source code is copied into the image at build time. Rebuild after any source change:

```bash
docker compose build --no-cache connectome
```

Alternatively, mount the source directory for development:

```yaml
# In docker-compose.yml, under volumes:
- ./source:/workspace/connectome/source
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop or `sudo systemctl start docker` |
| Out of memory during tractography | Increase Docker memory limit in Docker Desktop → Settings → Resources |
| Missing NIfTI files | Verify host `./data/raw/` contains the required files |
| 3-D figures not saved | Fury requires a display; set `save_3d_figures: false` in config or use a virtual display (`Xvfb`) |
