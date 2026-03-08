"""
rat_connectome
==============
Rat structural connectome pipeline.

Modules
-------
streamline_utils
    Core utility functions for streamline processing and I/O.
connectome_matrix_pipeline
    Stage 1: tractography and W/D/V matrix computation.
gaussian_tau_pipeline
    Stage 2: tau and FA matrix computation.
statistics_utils
    Statistical tests (KS, Mann–Whitney U, Cohen's d) and plotting.
structural_connectivity_analysis
    Stage 3: group-level structural connectivity analysis.
logging_config
    Centralised logging configuration.
"""

__version__ = "1.0.0"
__author__ = "Alejandro Aguado"
