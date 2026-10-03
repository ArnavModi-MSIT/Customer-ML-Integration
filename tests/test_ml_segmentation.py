"""Verify customer identity, deterministic assignments, and saved inference."""
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.ml_segmentation import FEATURES, run_ml_segmentation


class ClusteringTests(unittest.TestCase):
    def test_export_and_saved_inference(self):
        rng = np.random.default_rng(7)
        count = 60
        rfm = pd.DataFrame({
            "customer_unique_id": [str(i) for i in range(count)],
            "recency": rng.integers(1, 400, count),
            "frequency": rng.integers(1, 5, count),
            "monetary": rng.uniform(10, 1000, count),
            "Segment": ["Need Attention"] * count,
        })
        with tempfile.TemporaryDirectory() as directory:
            tables = run_ml_segmentation(rfm, directory, verbose=False)
            result = tables["ml_customer_clusters"]
            self.assertEqual(result.customer_unique_id.tolist(), rfm.customer_unique_id.tolist())
            self.assertEqual(tables["ml_cluster_profiles"].customer_count.sum(), count)
            self.assertEqual(tables["ml_model_selection"].selected.sum(), 1)
            bundle = joblib.load(Path(directory) / "customer_clustering.joblib")
            np.testing.assert_array_equal(bundle["pipeline"].predict(rfm[FEATURES]), result.ml_cluster)
            repeated = run_ml_segmentation(rfm, directory, verbose=False)
            np.testing.assert_array_equal(repeated["ml_customer_clusters"].ml_cluster, result.ml_cluster)
            rfm.loc[0, "monetary"] = np.nan
            with self.assertRaises(ValueError):
                run_ml_segmentation(rfm, directory, verbose=False)


if __name__ == "__main__":
    unittest.main()
