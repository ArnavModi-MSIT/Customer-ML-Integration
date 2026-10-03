"""Descriptive analytics: revenue, order, customer, review, and category metrics — pure aggregation, no modeling."""
import pandas as pd
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")


def compute_revenue_metrics(fact_orders):
    delivered = fact_orders[fact_orders["order_status"] == "delivered"]
    return {
        "total_revenue": delivered["total_value"].sum(),
        "avg_order_value": delivered["total_value"].mean(),
        "median_order_value": delivered["total_value"].median(),
        "min_order_value": delivered["total_value"].min(),
        "max_order_value": delivered["total_value"].max(),
    }


def compute_order_metrics(fact_orders, fact_order_items):
    total_orders = len(fact_orders)
    delivered_orders = len(fact_orders[fact_orders["order_status"] == "delivered"])
    canceled_orders = len(fact_orders[fact_orders["order_status"] == "canceled"])
    return {
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "delivered_pct": round((delivered_orders / total_orders) * 100, 1),
        "canceled_orders": canceled_orders,
        "avg_items_per_order": round(len(fact_order_items) / total_orders, 2),
    }


def compute_customer_metrics(dim_customers, fact_orders):
    """Uses customer_unique_id, not the per-order customer_id, for repeat-purchase metrics."""
    repeat_customers = fact_orders.groupby("customer_unique_id").size()
    repeat_rate = (
        len(repeat_customers[repeat_customers > 1]) / dim_customers["customer_unique_id"].nunique()
    ) * 100

    return {
        "unique_customers": dim_customers["customer_unique_id"].nunique(),
        "unique_states": dim_customers["customer_state"].nunique(),
        "unique_cities": dim_customers["customer_city"].nunique(),
        "repeat_purchase_rate_pct": round(repeat_rate, 2),
        "avg_orders_per_customer": round(len(fact_orders) / dim_customers["customer_unique_id"].nunique(), 2),
    }


def compute_review_metrics(reviews):
    reviews = reviews.copy()
    reviews["review_score"] = pd.to_numeric(reviews["review_score"], errors="coerce")
    return {
        "total_reviews": len(reviews),
        "avg_rating": round(reviews["review_score"].mean(), 2),
        "median_rating": round(reviews["review_score"].median(), 2),
        "std_rating": round(reviews["review_score"].std(), 2),
        "rating_distribution": reviews["review_score"].value_counts().sort_index().to_dict(),
    }


def compute_category_metrics(fact_order_items, dim_products, top_n=10):
    merged = fact_order_items.merge(
        dim_products[["product_id", "product_category_name_english"]], on="product_id", how="left"
    )
    merged["product_category_name_english"] = merged["product_category_name_english"].fillna("unknown")

    top_categories = (
        merged.groupby("product_category_name_english")["price"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )
    return top_categories.round(2).to_dict()


def compute_top_products(fact_order_items, dim_products, fact_orders, top_n=20):
    """Pre-ranked so Power BI doesn't have to rank ~33K products live in DAX. Delivered orders only."""
    delivered_order_ids = fact_orders.loc[fact_orders["order_status"] == "delivered", "order_id"]
    delivered_items = fact_order_items[fact_order_items["order_id"].isin(delivered_order_ids)]

    merged = delivered_items.merge(
        dim_products[["product_id", "product_category_name_english"]], on="product_id", how="left"
    )
    merged["product_category_name_english"] = merged["product_category_name_english"].fillna("unknown")

    return (
        merged.groupby(["product_id", "product_category_name_english"])["price"]
        .sum()
        .reset_index()
        .rename(columns={"price": "total_revenue"})
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def data_quality_checks(dim_customers, fact_orders, fact_order_items, reviews):
    return {
        "no_duplicate_customer_ids": dim_customers["customer_id"].duplicated().sum() == 0,
        "no_duplicate_order_ids": fact_orders["order_id"].duplicated().sum() == 0,
        "prices_positive": bool((fact_order_items["price"] > 0).all()),
        "freight_non_negative": bool((fact_order_items["freight_value"] >= 0).all()),
        "valid_review_scores": bool(reviews["review_score"].between(1, 5).all()),
    }


def run_eda(tables, verbose=True):
    fact_orders = tables["fact_orders"]
    fact_order_items = tables["fact_order_items"]
    dim_customers = tables["dim_customers"]
    dim_products = tables["dim_products"]
    reviews = tables["reviews"]

    revenue = compute_revenue_metrics(fact_orders)
    order_metrics = compute_order_metrics(fact_orders, fact_order_items)
    customer_metrics = compute_customer_metrics(dim_customers, fact_orders)
    review_metrics = compute_review_metrics(reviews)
    category_metrics = compute_category_metrics(fact_order_items, dim_products)
    quality = data_quality_checks(dim_customers, fact_orders, fact_order_items, reviews)

    summary = {
        "generated_at": datetime.now().isoformat(),
        "revenue": revenue,
        "orders": order_metrics,
        "customers": customer_metrics,
        "reviews": review_metrics,
        "top_categories_by_revenue": category_metrics,
        "data_quality": quality,
    }

    if verbose:
        print("=" * 80)
        print("EDA SUMMARY")
        print("=" * 80)
        print(f"Total Revenue: R$ {revenue['total_revenue']:,.2f}")
        print(f"Avg Order Value (per order, corrected): R$ {revenue['avg_order_value']:,.2f}")
        print(f"Median Order Value: R$ {revenue['median_order_value']:,.2f}")
        print(f"Total Orders: {order_metrics['total_orders']:,} | Delivered: {order_metrics['delivered_pct']}%")
        print(f"Unique Customers: {customer_metrics['unique_customers']:,}")
        print(f"Repeat Purchase Rate: {customer_metrics['repeat_purchase_rate_pct']}%")
        print(f"Avg Rating: {review_metrics['avg_rating']}/5.0")
        print("Top 5 Categories by Revenue:")
        for cat, rev in list(category_metrics.items())[:5]:
            print(f"  {cat}: R$ {rev:,.2f}")
        print("Data Quality:", quality)
        print("=" * 80)

    return summary


if __name__ == "__main__":
    from prepare_data import run_prepare_data

    tables = run_prepare_data()
    run_eda(tables)
