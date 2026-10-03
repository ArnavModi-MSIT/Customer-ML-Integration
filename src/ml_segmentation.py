"""Exploratory customer clustering; does not predict churn or retention ROI."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

FEATURES = ["recency", "frequency", "monetary"]
SEED = 42


def run_ml_segmentation(rfm, output_dir, verbose=True):
    """Select k=2..6 by sampled silhouette after log1p and standard scaling.

    Customer IDs and rule-based labels are excluded from training. All customers
    are used for exploratory clustering; silhouette is not predictive accuracy.
    """
    features = rfm[FEATURES].astype(float)
    if not np.isfinite(features.to_numpy()).all() or (features < 0).any().any():
        raise ValueError("ML features must be finite and nonnegative.")
    unique_count = len(features.drop_duplicates())
    max_k = min(6, unique_count - 1, len(features) - 1)
    if max_k < 2:
        raise ValueError("Clustering needs at least three distinct customer profiles.")

    preprocessing = Pipeline([
        ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
        ("scale", StandardScaler()),
    ])
    transformed = preprocessing.fit_transform(features)
    candidates = []
    models = {}
    # Use the same bounded customer sample for each candidate.
    rng = np.random.default_rng(SEED)
    indices = rng.choice(len(features), size=min(2000, len(features)), replace=False)
    for k in range(2, max_k + 1):
        model = KMeans(n_clusters=k, random_state=SEED, n_init=10)
        labels = model.fit_predict(transformed)
        sample_labels = labels[indices]
        score = (
            silhouette_score(transformed[indices], sample_labels)
            if 1 < len(np.unique(sample_labels)) < len(indices) else np.nan
        )
        candidates.append({"k": k, "silhouette_score": score, "inertia": model.inertia_,
                           "smallest_cluster": int(np.bincount(labels, minlength=k).min()),
                           "sample_size": len(indices)})
        models[k] = model
    metrics = pd.DataFrame(candidates)
    valid = metrics.dropna(subset=["silhouette_score"])
    if valid.empty:
        raise ValueError("No candidate has a valid silhouette score.")
    best_k = int(valid.sort_values(["silhouette_score", "k"], ascending=[False, True]).iloc[0]["k"])
    metrics["selected"] = metrics["k"].eq(best_k)
    model = models[best_k]

    customers = rfm.copy()
    customers["ml_cluster"] = model.labels_
    profiles = customers.groupby("ml_cluster").agg(
        customer_count=("customer_unique_id", "size"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_monetary=("monetary", "sum"),
    ).reset_index()
    profiles["customer_share_pct"] = profiles["customer_count"] / len(customers) * 100
    profiles["revenue_share_pct"] = profiles["total_monetary"] / customers["monetary"].sum() * 100
    profiles = profiles.round(2)
    comparison = customers.groupby(["ml_cluster", "Segment"]).size().reset_index(name="customer_count")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {"ml_customer_clusters": customers, "ml_cluster_profiles": profiles,
              "ml_model_selection": metrics, "ml_rfm_comparison": comparison}
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
    pipeline = Pipeline(preprocessing.steps + [("kmeans", model)])
    joblib.dump({"pipeline": pipeline, "features": FEATURES,
                 "random_seed": SEED,
                 "purpose": "Exploratory RFM clustering, not churn prediction"},
                output_dir / "customer_clustering.joblib")
    if verbose:
        print(f"ML clustering: selected k={best_k} by sampled silhouette")
        print(metrics.to_string(index=False))
        print(profiles.to_string(index=False))
    return tables
