"""Reads raw Olist CSVs and builds clean, joined tables for RFM scoring and Power BI. Pure pandas — no database."""
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

RAW_FILES = {
    "dim_customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "dim_sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}
PRODUCTS_FILE = "olist_products_dataset.csv"
TRANSLATION_FILE = "product_category_name_translation.csv"


def load_raw_tables(verbose=True):
    """Reads every raw CSV into a dict of DataFrames, keyed by table name."""
    tables = {}
    for name, fname in RAW_FILES.items():
        path = os.path.join(RAW_DIR, fname)
        tables[name] = pd.read_csv(path, low_memory=False)
        if verbose:
            print(f"  loaded {name}: {len(tables[name]):,} rows")

    tables["dim_products"] = load_products_with_translation(verbose=verbose)
    return tables


def load_products_with_translation(verbose=True):
    """Fills missing categories as 'unknown' (dropping rows would orphan order_items) and joins English category names."""
    products = pd.read_csv(os.path.join(RAW_DIR, PRODUCTS_FILE), low_memory=False)
    translation = pd.read_csv(os.path.join(RAW_DIR, TRANSLATION_FILE))

    products["product_category_name"] = products["product_category_name"].fillna("unknown")
    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name_english"] = products["product_category_name_english"].fillna(
        products["product_category_name"]
    )
    if verbose:
        print(f"  loaded dim_products: {len(products):,} rows (cleaned + English category names)")
    return products


def build_fact_order_items(order_items):
    """One row per order line item, with price + freight combined into total_value."""
    order_items = order_items.copy()
    order_items["price"] = pd.to_numeric(order_items["price"], errors="coerce")
    order_items["freight_value"] = pd.to_numeric(order_items["freight_value"], errors="coerce")
    order_items["total_value"] = order_items["price"] + order_items["freight_value"]
    return order_items


def build_fact_orders(orders, dim_customers, fact_order_items, reviews, verbose=True):
    """One row per order, with item totals summed (not averaged) and true customer identity attached."""
    order_totals = fact_order_items.groupby("order_id")["total_value"].sum().reset_index()

    before = orders["order_id"].nunique()
    fact = orders.merge(order_totals, on="order_id", how="inner")
    dropped = before - fact["order_id"].nunique()

    fact = fact.merge(
        dim_customers[["customer_id", "customer_unique_id", "customer_state", "customer_city"]],
        on="customer_id",
        how="left",
    )
    fact = fact.merge(reviews.groupby("order_id")["review_score"].mean().reset_index(), on="order_id", how="left")
    fact["order_purchase_timestamp"] = pd.to_datetime(fact["order_purchase_timestamp"])

    if verbose and dropped:
        print(f"  dropped {dropped:,} orders with no line items (can't have a total_value)")

    return fact


def build_dim_geolocation(geolocation):
    """Collapses the raw geolocation table (many lat/lng rows per zip prefix) to one row per zip."""
    return (
        geolocation.groupby("geolocation_zip_code_prefix")
        .agg(
            lat=("geolocation_lat", "mean"),
            lng=("geolocation_lng", "mean"),
            city=("geolocation_city", "first"),
            state=("geolocation_state", "first"),
        )
        .reset_index()
        .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
    )


def run_prepare_data(verbose=True):
    if verbose:
        print("=" * 80)
        print("PREPARE DATA")
        print("=" * 80)

    raw = load_raw_tables(verbose=verbose)
    fact_order_items = build_fact_order_items(raw["order_items"])
    fact_orders = build_fact_orders(raw["orders"], raw["dim_customers"], fact_order_items, raw["reviews"], verbose=verbose)
    dim_geolocation = build_dim_geolocation(raw["geolocation"])

    tables = {
        "fact_orders": fact_orders,
        "fact_order_items": fact_order_items,
        "dim_customers": raw["dim_customers"],
        "dim_products": raw["dim_products"],
        "dim_sellers": raw["dim_sellers"],
        "dim_geolocation": dim_geolocation,
        "payments": raw["payments"],
        "reviews": raw["reviews"],
    }

    if verbose:
        print(f"✓ fact_orders: {len(fact_orders):,} rows")
        print("=" * 80)

    return tables


if __name__ == "__main__":
    run_prepare_data()
