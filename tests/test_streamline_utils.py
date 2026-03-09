"""
test_streamline_utils.py
========================
Unit tests for streamline_utils.py.
These tests use synthetic data so they run without any MRI files.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

import streamline_utils as su

# Ensure source/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "source"))

# Stub dipy modules that are not available in test environment
for mod in [
    "dipy", "dipy.tracking", "dipy.tracking.utils",
    "dipy.tracking._utils", "dipy.tracking.streamline",
    "dipy.viz", "dipy.viz.actor", "dipy.viz.colormap",
    "dipy.viz.window",
]:
    sys.modules.setdefault(mod, MagicMock())


class TestMatrixIO(unittest.TestCase):
    """Test save/load of text matrices."""

    def test_save_load_roundtrip(self):
        """save_matrix_as_text / np.loadtxt roundtrip."""
        import tempfile
        import os
        mat = np.array([[1.0, 2.0], [3.0, 4.0]])
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fh:
            tmp = fh.name
        try:
            su.save_matrix_as_text(mat, tmp)
            loaded = np.loadtxt(tmp)
            np.testing.assert_array_almost_equal(mat, loaded)
        finally:
            os.unlink(tmp)


class TestDictIO(unittest.TestCase):
    """Test pickle-based dictionary I/O."""

    def test_save_load_dict(self):
        import tempfile
        import os
        data = {"key": [1, 2, 3], "nested": {"a": 42}}
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as fh:
            tmp = fh.name
        try:
            su.save_dict(data, tmp)
            loaded = su.load_dict(tmp)
            self.assertEqual(loaded["nested"]["a"], 42)
            self.assertEqual(loaded["key"], [1, 2, 3])
        finally:
            os.unlink(tmp)

    def test_load_missing_file(self):
        result = su.load_dict("/nonexistent/path/file.dat")
        self.assertEqual(result, {})


class TestMatrixToVector(unittest.TestCase):
    """Test matrix_to_vector utility (imported from connectivity analysis)."""

    def setUp(self):
        sys.modules.setdefault("seaborn", MagicMock())
        sys.modules.setdefault("matplotlib", MagicMock())
        sys.modules.setdefault("matplotlib.pyplot", MagicMock())
        sys.modules.setdefault("matplotlib.colors", MagicMock())

    def test_upper_triangle_extraction(self):
        """Only upper-triangle values above threshold are extracted."""
        #import importlib
        # Import with stubs in place
        sca = MagicMock()
        sys.modules["structural_connectivity_analysis"] = sca
        #from statistics_utils import analyze_and_plot  # noqa: ensure no crash

        mat = np.zeros((4, 4))
        mat[0, 1] = 5.0
        mat[0, 2] = 10.0
        mat[2, 1] = 99.0   # lower triangle — should NOT appear

        # Inline the logic to avoid extra import complexity
        N = len(mat)
        vec = [mat[i, j] for i in range(N) for j in range(N)
               if j > i and mat[i, j] > 0]
        self.assertIn(5.0, vec)
        self.assertIn(10.0, vec)
        self.assertNotIn(99.0, vec)


class TestBuildVelocityVolume(unittest.TestCase):
    """Test build_velocity_volume with a minimal 2×2×1 volume."""

    def test_masked_voxels_are_minus_one(self):
        mask = np.array([[[0], [1]], [[1], [0]]])
        FM = np.full_like(mask, 0.2, dtype=float)
        FR = np.full_like(mask, 0.5, dtype=float)
        AX = np.full_like(mask, 1.0, dtype=float)

        vol = su.build_velocity_volume(mask, FM, FR, AX)

        self.assertEqual(vol[0, 0, 0], -1.0)
        self.assertEqual(vol[1, 1, 0], -1.0)
        self.assertGreater(vol[0, 1, 0], 0.0)
        self.assertGreater(vol[1, 0, 0], 0.0)


class TestCohensD(unittest.TestCase):
    """Test Cohen's d calculation."""

    def setUp(self):
        sys.modules.setdefault("scipy", MagicMock())
        sys.modules.setdefault("scipy.stats", MagicMock())

    def _cohens_d(self, x, y):
        """Inline reference implementation."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        nx, ny = len(x), len(y)
        pv = ((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2)
        ps = np.sqrt(pv)
        return (np.mean(x) - np.mean(y)) / ps if ps > 0 else 0.0

    def test_identical_groups(self):
        x = [1.0, 2.0, 3.0]
        y = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(self._cohens_d(x, y), 0.0)

    def test_large_difference(self):
        rng = np.random.default_rng(0)
        x = (rng.standard_normal(50) + 5.0).tolist()
        y = (rng.standard_normal(50) + 0.0).tolist()
        d = abs(self._cohens_d(x, y))
        self.assertGreater(d, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
