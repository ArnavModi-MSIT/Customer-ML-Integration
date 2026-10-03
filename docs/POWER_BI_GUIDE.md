# Building the Power BI Dashboard

This walks through building the report from scratch in Power BI Desktop, using
`data/processed/olist_analytics.xlsx` (produced by `python run_pipeline.py`) as
the only data source — no database connection involved.

If you don't have Power BI Desktop yet: it's a free download from
[Microsoft](https://www.microsoft.com/en-us/power-platform/products/power-bi/downloads).

---

## 1. Import the data

1. Open Power BI Desktop → **Get Data** → **Excel workbook** → select
   `data/processed/olist_analytics.xlsx`.
2. In the Navigator, check every sheet (all 10) and click **Transform Data**
   rather than Load — this opens Power Query so you can fix data types before
   they hit the model.
3. In Power Query, for each table check that Power BI guessed the right type
   for date/number columns (it usually gets `order_purchase_timestamp` right,
   but double check numeric columns like `total_value` aren't imported as
   text). Click **Close & Apply**.

You now have 10 tables in the model: `fact_orders`, `fact_order_items`,
`dim_customers`, `dim_products`, `dim_sellers`, `dim_geolocation`, `payments`,
`reviews`, `rfm_customer_segments`, `segment_summary`.

## 2. Build the relationships (star schema)

Go to **Model view** (left sidebar) and create these relationships by
dragging from one column to the other. All should be **one-to-many**, single
direction (arrow pointing from the "one" side to the "many" side):

| From (one) | To (many) | Key |
|---|---|---|
| `dim_customers` | `fact_orders` | `customer_id` |
| `dim_customers` | `fact_order_items`* | — (see note) |
| `fact_orders` | `fact_order_items` | `order_id` |
| `dim_products` | `fact_order_items` | `product_id` |
| `dim_sellers` | `fact_order_items` | `seller_id` |
| `fact_orders` | `payments` | `order_id` |
| `fact_orders` | `reviews` | `order_id` |
| `rfm_customer_segments` | `dim_customers`** | `customer_unique_id` |

\* `fact_order_items` doesn't carry `customer_id` directly — it relates to
customers *through* `fact_orders`. Don't force a direct relationship there;
let Power BI's relationship traversal handle it through `order_id`.

\** `dim_customers` has `customer_id` (per-order key) and `customer_unique_id`
(true customer identity) as two different columns. `rfm_customer_segments` is
keyed on `customer_unique_id` — relate on that column specifically, not
`customer_id`. This is the same identity distinction the Python pipeline
handles (see the comment in `src/eda.py`).

Your model view should look like a star: `fact_orders` and `fact_order_items`
in the middle, dimension tables radiating out.

## 3. Write the DAX measures

Create a new table for measures to keep them organized: **Modeling** →
**New Table**, name it `_Measures`, formula: `_Measures = ROW("x", 0)`. Hide
its one column, then right-click it → **New Measure** for each of these:

```dax
Total Revenue = SUM(fact_orders[total_value])

Total Orders = DISTINCTCOUNT(fact_orders[order_id])

Avg Order Value = DIVIDE([Total Revenue], [Total Orders])

Unique Customers = DISTINCTCOUNT(fact_orders[customer_unique_id])

Repeat Purchase Rate =
VAR CustomerOrderCounts =
    SUMMARIZE(fact_orders, fact_orders[customer_unique_id], "Orders", COUNT(fact_orders[order_id]))
VAR RepeatCustomers =
    COUNTROWS(FILTER(CustomerOrderCounts, [Orders] > 1))
RETURN
    DIVIDE(RepeatCustomers, [Unique Customers])

Avg Rating = AVERAGE(fact_orders[review_score])

Revenue by Segment =
CALCULATE([Total Revenue], USERELATIONSHIP(rfm_customer_segments[customer_unique_id], dim_customers[customer_unique_id]))

At Risk Revenue =
CALCULATE(
    SUM(rfm_customer_segments[monetary]),
    rfm_customer_segments[Segment] IN {"At Risk", "Need Attention", "Lost"}
)
```

`Total Revenue` should read back **R$15,419,773.75** and `Unique Customers`
should read **96,096** — those match the numbers `python run_pipeline.py`
printed to your console. If they don't match, the relationships are wrong
somewhere — check the filter direction on each join.

## 4. Build the pages

Create 4 report pages (right-click the page tab at the bottom → rename).
For every page, start with a **Card** or **Multi-row card** visual for the
top KPIs, then add the detail visuals below.

### Page 1 — Executive Overview
- 5 **Card** visuals across the top: `Total Revenue`, `Total Orders`,
  `Avg Order Value`, `Unique Customers`, `Repeat Purchase Rate`
- **Line chart**: X-axis = `fact_orders[order_purchase_timestamp]` (set to
  Month granularity), Y-axis = `Total Revenue`
- **Card**: `At Risk Revenue`, with a text box below explaining what it means

### Page 2 — Customer & RFM Segmentation
- **Stacked bar chart**: X-axis = `rfm_customer_segments[Segment]`,
  Y-axis = `Revenue by Segment`
- **Table**: `segment_summary` sheet's columns directly (it's already a
  finished summary table — `Segment`, `customer_count`, `avg_recency`,
  `avg_frequency`, `avg_monetary`, `revenue_share_pct`)
- **Donut chart**: customer count by `Segment`, to show the size imbalance
  (Need Attention is ~40% of customers — this should visibly dominate)

### Page 3 — Product & Category Performance
- **Bar chart**: X-axis = `dim_products[product_category_name_english]`,
  Y-axis = SUM of `fact_order_items[price]`, sorted descending, top 10 via
  a Top N filter
- **Table**: top products by revenue (group `fact_order_items` by
  `product_id`, join to `dim_products` for the name)

### Page 4 — Geography
- **Map or filled map visual**: `dim_customers[customer_state]` (Brazilian
  state codes), size/color = `Total Revenue`
- **Bar chart**: revenue by state, sorted descending, for the states a map
  can't label clearly

## 5. Add a segment slicer

On pages 2–4, add a **Slicer** visual bound to `rfm_customer_segments[Segment]`
so a viewer can filter every visual down to e.g. just "At Risk" customers.
This is what makes it feel like a real tool rather than a static report —
cross-filtering is Power BI's main advantage over a plain chart.

## 6. Publish

**File** → **Publish** → **Publish to Power BI** (needs a free Power BI
account). Once published, go to the report in the Power BI service, **File**
→ **Embed report** → **Publish to web (public)** to get the same kind of
`app.powerbi.com/view?r=...` embed URL already used in `docs/index.html`.
Swap that URL in once you have your new one.

---

## Refreshing with new data

Since the source is now a plain Excel file instead of a live database, "refresh"
means: re-run `python run_pipeline.py` (with updated files in `data/raw/`) to
regenerate `olist_analytics.xlsx`, then in Power BI Desktop click **Refresh**
on the Home ribbon. No credentials, no server — just re-run the script and
click refresh.


## ML customer clustering page

After rerunning the pipeline, use **Get Data → Excel** to import the four
`ml_` sheets. Existing report refresh alone will not automatically import new
sheets. Add a fifth page for ML clustering:

- Bar chart: `ml_cluster_profiles[ml_cluster]` and `[customer_count]`.
- Table: cluster, average recency/frequency/monetary, and revenue share.
- Matrix: `ml_rfm_comparison[ml_cluster]` as rows, `[Segment]` as columns,
  and SUM of `[customer_count]` as values.
- Model selection table: k, silhouette_score, smallest_cluster, and selected.

For order filtering, relate `ml_customer_clusters[customer_unique_id]` (one)
to `fact_orders[customer_unique_id]` (many), single direction. Relate
`ml_cluster_profiles[ml_cluster]` (one) to
`ml_customer_clusters[ml_cluster]` (many), single direction, and use the
profile cluster column for a slicer. Avoid bidirectional paths through the
existing RFM table. The model-selection and comparison tables can remain
disconnected for their own visuals.

Label this page **Exploratory ML Customer Groups**. Cluster numbers are
arbitrary, and refitting can change them. Silhouette is a separation score,
not churn accuracy. Retention ROI remains a scenario based on historical spend.
