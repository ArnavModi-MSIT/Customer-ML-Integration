"""Business insights derived directly from RFM segmentation — no ML, just sums and percentages."""
from datetime import datetime


def revenue_concentration(segment_summary):
    top_segment = segment_summary.iloc[0]
    return {
        "top_segment": top_segment["Segment"],
        "top_segment_customer_pct": top_segment["pct_of_customers"],
        "top_segment_revenue_pct": top_segment["revenue_share_pct"],
    }


def at_risk_revenue(rfm):
    """'At risk' = the At Risk, Need Attention, and Lost segments — not a model's prediction."""
    at_risk_segments = ["At Risk", "Need Attention", "Lost"]
    at_risk = rfm[rfm["Segment"].isin(at_risk_segments)]
    total_revenue = rfm["monetary"].sum()
    return {
        "at_risk_customer_count": int(len(at_risk)),
        "at_risk_revenue": round(at_risk["monetary"].sum(), 2),
        "at_risk_pct_of_customers": round(len(at_risk) / len(rfm) * 100, 2),
        "at_risk_pct_of_revenue": round(at_risk["monetary"].sum() / total_revenue * 100, 2),
    }


def retention_roi_scenarios(rfm, retention_rates=(10, 20, 30)):
    """Revenue impact of re-engaging X% of the 'At Risk' segment back to their historical spend."""
    at_risk = rfm[rfm["Segment"] == "At Risk"]
    at_risk_revenue_total = at_risk["monetary"].sum()
    total_revenue = rfm["monetary"].sum()

    scenarios = []
    for rate in retention_rates:
        recovered = at_risk_revenue_total * rate / 100
        scenarios.append({
            "retention_rate_pct": rate,
            "recovered_revenue": round(recovered, 2),
            "growth_pct": round(recovered / total_revenue * 100, 2),
        })
    return scenarios


def run_business_insights(rfm, segment_summary, verbose=True):
    concentration = revenue_concentration(segment_summary)
    risk = at_risk_revenue(rfm)
    roi = retention_roi_scenarios(rfm)

    if verbose:
        print("=" * 80)
        print("BUSINESS INSIGHTS")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(
            f"\n{concentration['top_segment']} are {concentration['top_segment_customer_pct']}% of customers "
            f"and generate {concentration['top_segment_revenue_pct']}% of revenue."
        )
        print(
            f"\nAt-risk revenue (At Risk + Need Attention + Lost segments): "
            f"R$ {risk['at_risk_revenue']:,.2f} ({risk['at_risk_pct_of_revenue']}% of total)"
        )
        print("\nRetention ROI scenarios (recovering a % of 'At Risk' segment spend):")
        for s in roi:
            print(f"  Retain {s['retention_rate_pct']}%: +R$ {s['recovered_revenue']:,.2f} ({s['growth_pct']}% growth)")
        print("=" * 80)

    return {"concentration": concentration, "at_risk": risk, "roi_scenarios": roi}


if __name__ == "__main__":
    from prepare_data import run_prepare_data
    from rfm import run_rfm

    tables = run_prepare_data()
    rfm, segment_summary = run_rfm(tables["fact_orders"])
    run_business_insights(rfm, segment_summary)
