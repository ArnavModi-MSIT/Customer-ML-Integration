"""RFM (Recency, Frequency, Monetary) customer segmentation — rule-based quantile scoring, no ML."""
import pandas as pd
from datetime import timedelta
import warnings

warnings.filterwarnings("ignore")


def calculate_rfm(fact_orders):
    """Only 'delivered' orders count toward RFM."""
    delivered = fact_orders[fact_orders["order_status"] == "delivered"].copy()
    analysis_date = delivered["order_purchase_timestamp"].max() + timedelta(days=1)

    rfm = delivered.groupby("customer_unique_id").agg(
        recency=("order_purchase_timestamp", lambda x: (analysis_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("total_value", "sum"),
        avg_rating=("review_score", "mean"),
    ).reset_index()

    # Most-recent state per customer (customers can have multiple recorded states across orders)
    latest_state = (
        delivered.sort_values("order_purchase_timestamp")
        .groupby("customer_unique_id")["customer_state"]
        .last()
        .reset_index()
    )
    rfm = rfm.merge(latest_state, on="customer_unique_id", how="left")

    return rfm, analysis_date


def score_rfm(rfm):
    rfm = rfm.copy()
    rfm["R_score"] = pd.to_numeric(pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop"))
    rfm["F_score"] = pd.to_numeric(
        pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    )
    rfm["M_score"] = pd.to_numeric(
        pd.qcut(rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    )
    rfm["RFM_Score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]
    rfm["RFM_Score_Avg"] = rfm["RFM_Score"] / 3
    return rfm


def segment_customer(row):
    r, f, m = row["R_score"], row["F_score"], row["M_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif r >= 4 and f >= 3 and m >= 3:
        return "Loyal Customers"
    elif r >= 3 and f >= 1 and m >= 3:
        return "Potential Loyalist"
    elif r >= 4 and f <= 2 and m <= 2:
        return "New Customers"
    elif r <= 2 and f >= 3 and m >= 3:
        return "At Risk"
    elif r <= 1 and f <= 2 and m <= 2:
        return "Lost"
    else:
        return "Need Attention"


def summarize_segments(rfm):
    summary = rfm.groupby("Segment").agg(
        customer_count=("customer_unique_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        avg_rating=("avg_rating", "mean"),
        avg_rfm_score=("RFM_Score_Avg", "mean"),
    ).round(2)

    total_customers = len(rfm)
    total_revenue = rfm["monetary"].sum()
    summary["pct_of_customers"] = (summary["customer_count"] / total_customers * 100).round(2)
    summary["revenue_share_pct"] = (rfm.groupby("Segment")["monetary"].sum() / total_revenue * 100).round(2)

    return summary.sort_values("avg_rfm_score", ascending=False).reset_index()


def run_rfm(fact_orders, verbose=True):
    rfm, analysis_date = calculate_rfm(fact_orders)
    rfm = score_rfm(rfm)
    rfm["Segment"] = rfm.apply(segment_customer, axis=1)

    segment_summary = summarize_segments(rfm)

    if verbose:
        print("=" * 80)
        print("RFM ANALYSIS")
        print("=" * 80)
        print(f"Analysis date: {analysis_date.date()}")
        print(f"Customers analyzed (customer_unique_id): {len(rfm):,}")
        print(f"Max frequency observed: {rfm['frequency'].max()} (sanity check — should be small, not inflated)")
        print()
        print(segment_summary.to_string(index=False))
        print("=" * 80)

    return rfm, segment_summary


if __name__ == "__main__":
    from prepare_data import run_prepare_data

    tables = run_prepare_data()
    rfm, segment_summary = run_rfm(tables["fact_orders"])
