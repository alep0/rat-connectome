"""
validate_environment.py
========================
Validate the Python environment, required packages, and project
directory structure before running any pipeline.

Run as:
    python3 validations/validate_environment.py --root /workspace/connectome
"""

import importlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required packages
# ---------------------------------------------------------------------------
REQUIRED_PACKAGES = [
    "numpy",
    "matplotlib",
    "scipy",
    "seaborn",
    "dipy",
    "nibabel",
    "sklearn",
]

# Optional packages (warnings only)
OPTIONAL_PACKAGES = [
    "fury",
]

# Required project directories
REQUIRED_DIRS = [
    "source",
    "data",
    "data/raw",
    "data/processed",
    "docs",
    "logs",
    "validations",
    "results",
    "config",
    "scripts",
    "tests",
]

# Required config files
REQUIRED_CONFIG_FILES = [
    "config/connectome_config.json",
    "config/subjects.json",
]


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_python_version(min_major: int = 3, min_minor: int = 9) -> bool:
    """Check that Python meets the minimum version requirement."""
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (min_major, min_minor)
    status = "OK" if ok else "FAIL"
    logger.info(
        "[%s] Python version: %d.%d (required >= %d.%d)",
        status, major, minor, min_major, min_minor,
    )
    return ok


def validate_packages(packages: list, optional: bool = False) -> bool:
    """Check that all listed packages can be imported."""
    all_ok = True
    tag = "OPTIONAL" if optional else "REQUIRED"
    for pkg in packages:
        try:
            importlib.import_module(pkg)
            logger.info("[OK      ] %s package: %s", tag, pkg)
        except ImportError:
            level = logging.WARNING if optional else logging.ERROR
            logger.log(level, "[%s] %s package missing: %s",
                       "WARN" if optional else "MISSING", tag, pkg)
            if not optional:
                all_ok = False
    return all_ok


def validate_directories(root: Path) -> bool:
    """Check that all required project directories exist."""
    all_ok = True
    for rel_dir in REQUIRED_DIRS:
        full = root / rel_dir
        exists = full.is_dir()
        status = "OK" if exists else "MISSING"
        log_fn = logger.info if exists else logger.warning
        log_fn("[%s] Directory: %s", status, full)
        if not exists:
            all_ok = False
    return all_ok


def validate_config_files(root: Path) -> bool:
    """Check that key configuration files exist."""
    all_ok = True
    for rel_file in REQUIRED_CONFIG_FILES:
        full = root / rel_file
        exists = full.is_file()
        status = "OK" if exists else "MISSING"
        log_fn = logger.info if exists else logger.warning
        log_fn("[%s] Config file: %s", status, full)
        if not exists:
            all_ok = False
    return all_ok


def validate_source_modules(root: Path) -> bool:
    """Check that all source modules are importable."""
    source_dir = root / "source"
    modules = [
        "streamline_utils",
        "connectome_matrix_pipeline",
        "gaussian_tau_pipeline",
        "statistics_utils",
        "structural_connectivity_analysis",
        "logging_config",
    ]
    sys.path.insert(0, str(source_dir))
    all_ok = True
    for mod in modules:
        try:
            importlib.import_module(mod)
            logger.info("[OK     ] Source module: %s", mod)
        except ImportError as exc:
            logger.error("[MISSING] Source module %s: %s", mod, exc)
            all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_validation(root: str) -> int:
    """Run all validation checks.

    Parameters
    ----------
    root:
        Project root directory path.

    Returns
    -------
    int
        0 if all required checks pass, 1 otherwise.
    """
    root_path = Path(root)
    results = []

    logger.info("=" * 60)
    logger.info("Environment Validation — root: %s", root_path)
    logger.info("=" * 60)

    results.append(("Python version",  validate_python_version()))
    results.append(("Required packages", validate_packages(REQUIRED_PACKAGES)))
    validate_packages(OPTIONAL_PACKAGES, optional=True)
    results.append(("Project directories", validate_directories(root_path)))
    results.append(("Config files",       validate_config_files(root_path)))
    results.append(("Source modules",     validate_source_modules(root_path)))

    logger.info("=" * 60)
    logger.info("Validation Summary:")
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        log_fn = logger.info if passed else logger.error
        log_fn("  [%s] %s", status, name)
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("All required checks PASSED.")
    else:
        logger.error("One or more required checks FAILED.")
    logger.info("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate the connectome project environment.")
    parser.add_argument("--root",      required=True, help="Project root path")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    sys.exit(run_validation(args.root))
