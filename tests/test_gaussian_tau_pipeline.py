"""
test_gaussian_tau_pipeline.py
==============================
Unit tests for gaussian_tau_pipeline.py.
Uses synthetic streamline and velocity data.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from gaussian_tau_pipeline import compute_tau_per_roi_pair

# Path setup and dipy stubs
sys.path.insert(0, str(Path(__file__).parent.parent / "source"))
for mod in [
    "dipy", "dipy.tracking", "dipy.tracking.utils",
    "dipy.tracking._utils", "dipy.tracking.streamline",
    "dipy.viz", "dipy.viz.actor", "dipy.viz.colormap", "dipy.viz.window",
]:
    sys.modules.setdefault(mod, MagicMock())


class TestComputeTauPerROIPair(unittest.TestCase):
    """Test tau computation with synthetic fibres."""

    def _make_straight_streamline(self, n_points: int = 10) -> np.ndarray:
        """Create a straight streamline along x-axis."""
        return np.column_stack([
            np.linspace(0, 1, n_points),
            np.zeros(n_points),
            np.zeros(n_points),
        ])

    def test_all_fibres_accepted_at_zero_threshold(self):
        """All fibres should be accepted when threshold=0."""
        n_fibres = 5
        streamlines = [self._make_straight_streamline(10) for _ in range(n_fibres)]
        velocities  = [np.full(10, 5.0) for _ in range(n_fibres)]  # 5 m/s
        ax_data = fm_data = fr_data = fa_data = [np.ones(10) for _ in range(n_fibres)]

        records, dists, vels, taus, fas = compute_tau_per_roi_pair(
            streamlines, velocities, ax_data, fm_data, fr_data, fa_data,
            threshold=0.0,
        )

        self.assertEqual(len(records), n_fibres)
        self.assertEqual(len(taus), n_fibres)
        for tau in taus:
            self.assertGreater(tau, 0.0)

    def test_slow_voxels_filtered(self):
        """Fibres with all velocities < 1 m/s should be rejected at threshold=0."""
        streamlines = [self._make_straight_streamline(5)]
        velocities  = [np.full(5, 0.5)]   # all below 1 m/s
        ax_data = fm_data = fr_data = fa_data = [np.ones(5)]

        records, *_ = compute_tau_per_roi_pair(
            streamlines, velocities, ax_data, fm_data, fr_data, fa_data,
            threshold=0.0,
        )
        self.assertEqual(len(records), 0)

    def test_tau_formula(self):
        """tau = arc_length / median_velocity (scaled)."""
        pts = np.column_stack([np.arange(11, dtype=float), np.zeros(11), np.zeros(11)])
        # arc length contribution: each step is (2.27273, 0, 0) * [2.27273, 2.27273, 10]
        # = (2.27273 * 2.27273) per step × 10 steps
        streamlines = [pts]
        velocities  = [np.full(11, 2.0)]  # 2 m/s
        ax_data = fm_data = fr_data = fa_data = [np.ones(11)]

        records, dists, vels, taus, _ = compute_tau_per_roi_pair(
            streamlines, velocities, ax_data, fm_data, fr_data, fa_data,
            threshold=0.0,
        )

        self.assertEqual(len(taus), 1)
        expected_tau = dists[0] / 2.0
        self.assertAlmostEqual(taus[0], expected_tau, places=6)

    def test_empty_streamlines(self):
        """Empty input should return empty outputs without error."""
        records, dists, vels, taus, fas = compute_tau_per_roi_pair(
            [], [], [], [], [], [], threshold=0.0,
        )
        self.assertEqual(records, [])
        self.assertEqual(taus, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
