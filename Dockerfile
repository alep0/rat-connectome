# =============================================================================
# Dockerfile — Rat Structural Connectome Pipeline
# =============================================================================
# Base image: Miniconda3 on Debian slim
# Build:  docker compose build connectome
# Run:    docker compose run --rm connectome bash
# =============================================================================

FROM continuumio/miniconda3:23.10.0-1

LABEL maintainer="Alejandro Aguado"
LABEL description="Rat structural connectome pipeline (dipy, scipy, seaborn)"
LABEL version="1.0.0"

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libgomp1 \
        git \
        wget \
        curl \
        nano \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Conda environment
# ---------------------------------------------------------------------------
WORKDIR /workspace/connectome

COPY config/environment.yml ./config/environment.yml

RUN conda env create -f config/environment.yml \
    && conda clean -afy

# Make conda activate work in non-interactive shells
SHELL ["/bin/bash", "-c"]
RUN echo "conda activate rat-conn_env" >> ~/.bashrc

# ---------------------------------------------------------------------------
# Copy project source code
# ---------------------------------------------------------------------------
COPY source/      ./source/
COPY scripts/     ./scripts/
COPY validations/ ./validations/
COPY tests/       ./tests/
COPY config/      ./config/
COPY docs/        ./docs/

# ---------------------------------------------------------------------------
# Prepare runtime directories
# ---------------------------------------------------------------------------
RUN mkdir -p data/raw data/processed results logs

# ---------------------------------------------------------------------------
# Make all shell scripts executable
# ---------------------------------------------------------------------------
RUN chmod +x scripts/*.sh

# ---------------------------------------------------------------------------
# Set Python path so source/ is always importable
# ---------------------------------------------------------------------------
ENV PYTHONPATH="/workspace/connectome/source:${PYTHONPATH}"
ENV CONNECTOME_ROOT="/workspace/connectome"
ENV LOG_LEVEL="INFO"

# ---------------------------------------------------------------------------
# Default command — validate environment then show help
# ---------------------------------------------------------------------------
CMD ["/bin/bash", "-c", \
     "source activate rat-conn_env && \
      python3 validations/validate_environment.py --root /workspace/connectome && \
      echo 'Container ready. Use docker compose run --rm connectome bash to start a shell.'"]
