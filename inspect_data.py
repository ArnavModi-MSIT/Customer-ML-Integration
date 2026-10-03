import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")

FILES = [
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]


def inspect_file(path):
    df = pd.read_csv(path, low_memory=False)
    print(f"\n{os.path.basename(path)}")
    print("-" * 80)
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Dtypes:\n{df.dtypes}")
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print(f"Nulls:\n{nulls}")
    else:
        print("Nulls: none")
    return df


def main():
    dfs = {}
    for fname in FILES:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"\n⚠ MISSING: {fname}")
            continue
        dfs[fname] = inspect_file(path)

    # Key relationship checks
    if "olist_customers_dataset.csv" in dfs:
        cust = dfs["olist_customers_dataset.csv"]
        print("\n" + "=" * 80)
        print("CUSTOMER IDENTITY CHECK")
        print("=" * 80)
        print(f"customer_id (per-order key): {cust['customer_id'].nunique():,} unique")
        print(f"customer_unique_id (true identity): {cust['customer_unique_id'].nunique():,} unique")
        print("→ RFM/churn frequency MUST group by customer_unique_id, not customer_id")

    if "olist_orders_dataset.csv" in dfs and "olist_order_items_dataset.csv" in dfs:
        orders = dfs["olist_orders_dataset.csv"]
        items = dfs["olist_order_items_dataset.csv"]
        print("\n" + "=" * 80)
        print("ORDER / ORDER_ITEMS RELATIONSHIP CHECK")
        print("=" * 80)
        print(f"Total orders: {orders['order_id'].nunique():,}")
        print(f"Orders with items: {items['order_id'].nunique():,}")
        items_per_order = items.groupby("order_id").size()
        print(f"Orders with >1 item: {(items_per_order > 1).sum():,} ({(items_per_order > 1).mean()*100:.1f}%)")
        print("→ Order value stats must aggregate items to order_id BEFORE mean/median")

    if "olist_orders_dataset.csv" in dfs:
        orders = dfs["olist_orders_dataset.csv"]
        print("\n" + "=" * 80)
        print("ORDER STATUS DISTRIBUTION")
        print("=" * 80)
        print(orders["order_status"].value_counts())


if __name__ == "__main__":
    main()
