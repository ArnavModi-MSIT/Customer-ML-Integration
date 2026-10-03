# Customer Segmentation & Sales Analytics Dashboard

An analytics pipeline on the [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce):
RFM customer segmentation and sales/product/geography analytics, built with
Python + pandas + scikit-learn and visualized in Power BI. No database — raw CSVs go
in, a clean Excel workbook comes out, and that workbook is the single source
Power BI reads from.

**[Live Preview Dashboard](https://claude.ai/code/artifact/2bbd994f-825a-4324-8dd7-9cc6a1559240)** · **[Power BI Report](#)**

---

## Overview

- **96,096** unique customers analyzed across 99,441 orders
- **7-segment RFM model** (Champions, Loyal Customers, Potential Loyalist, At Risk, Need Attention, New Customers, Lost) — rule-based scoring, not ML
- **ML customer clustering**: log-transformed, standardized RFM features, K-means, and silhouette-based selection of 2–6 clusters
- **4-page Power BI dashboard**: Executive Overview, Customer/RFM Segmentation, Product & Category Performance, Geography
- Entire pipeline runs on a laptop with no server: `pip install`, run one script, open Power BI

## Key Findings

| Metric | Value |
|---|---|
| Total revenue (delivered orders) | R$15.4M |
| Champions revenue share | 13.15% (from 6.96% of customers) |
| Repeat purchase rate | 3.05% |
| Revenue at risk (At Risk + Need Attention + Lost) | R$7.0M (45.6% of total) |
| Recoverable revenue at 20% At Risk retention | +R$641K |

Customer purchase behavior in this dataset is heavily one-time-buyer skewed,
which shapes the segmentation: "Need Attention" is the largest single segment
at ~40% of customers. That single fact — most customers don't come back — is
the central story the dashboard is built to surface.

## Architecture

```
Raw Olist CSVs (data/raw/)
        │
        ▼
  Python: clean, join, RFM-score, ML clustering (pandas + scikit-learn)
        │
        ▼
  Excel workbook (data/processed/olist_analytics.xlsx)
        │
        ▼
  Power BI Desktop: relationships, DAX measures, 4-page report
```

RFM segmentation is rule-based (quantile buckets + threshold rules on
recency/frequency/monetary) — a real analytics technique companies use, not
machine learning. A separate K-means model learns customer groups from raw RFM
features; it does not predict churn or retention revenue. See [docs/POWER_BI_GUIDE.md](docs/POWER_BI_GUIDE.md) for why and how
that changes the retention-ROI framing.

## Tech Stack

Python · Pandas · scikit-learn · joblib · openpyxl · Power BI · DAX

## Project Structure

```
├── run_pipeline.py            # single entrypoint, runs all stages in order
├── inspect_data.py            # raw CSV schema/quality checker (run before anything else)
├── src/
│   ├── prepare_data.py        # raw CSVs → cleaned, joined star-schema tables (pandas)
│   ├── eda.py                 # revenue/order/customer/review metrics
│   ├── rfm.py                 # RFM scoring + 7-segment classification
│   ├── ml_segmentation.py    # K-means, model selection, profiles, persisted model
│   ├── business_insights.py   # revenue concentration, at-risk revenue, retention scenarios
│   └── export_to_excel.py     # writes every table to one Excel workbook
├── data/
│   ├── raw/                   # source CSVs (gitignored — see "Running It")
│   └── processed/             # olist_analytics.xlsx — the Power BI data source (gitignored)
├── docs/
│   ├── index.html             # project landing page
│   ├── style.css
│   └── POWER_BI_GUIDE.md      # step-by-step: build the report from the Excel workbook
├── analytics.pbix             # Power BI report file
└── outputs/                   # generated CSVs (rfm_analysis_results, segment_summary)
```

## Running It

```bash
pip install -r requirements.txt
```

Download the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
from Kaggle and place all 9 CSVs in `data/raw/`, then:

```bash
python inspect_data.py         # sanity-check the raw files
python run_pipeline.py         # prepare_data → eda → rfm → ml_segmentation → business_insights → export_to_excel
```

That produces `data/processed/olist_analytics.xlsx`. Open Power BI Desktop
and follow [docs/POWER_BI_GUIDE.md](docs/POWER_BI_GUIDE.md) to build the
report against it — no `.env`, no database, no credentials anywhere in this
project.

Each stage can also be run independently, e.g. `python src/eda.py`.

## ML integration

The ML stage learns customer groups from `recency`, `frequency`, and `monetary`.
It applies `log1p` to reduce skew, standardizes the features, and fits K-means
with a fixed seed and 10 initializations. It selects k from 2–6 using silhouette
on a fixed sample of up to 2,000 customers. IDs, ratings, and RFM labels are not
training features. Frequency is used directly, avoiding arbitrary quantile
ranks for customers with the same purchase count.

Generated CSVs and matching Excel sheets:

- `ml_customer_clusters`: customer-level RFM data plus `ml_cluster`.
- `ml_cluster_profiles`: cluster size, average RFM, and revenue shares.
- `ml_model_selection`: silhouette, inertia, smallest cluster, and selected k.
- `ml_rfm_comparison`: counts by ML cluster and existing rule-based segment.

`outputs/customer_clustering.joblib` stores preprocessing and the fitted model.
To assign customers with compatible RFM features, load the bundle and call
`bundle["pipeline"].predict(customer_features[bundle["features"]])`.
Only load trusted joblib files. Refitting can change cluster IDs, so interpret
profiles after each refresh rather than treating numeric IDs as permanent names.

Silhouette measures cluster separation, not predictive accuracy. These are
exploratory groups fitted on the historical dataset, with no held-out outcome
validation. They are not churn probabilities, causal recommendations, or
customer lifetime value predictions. Inspect the smallest cluster and the
profiles before using the groups for marketing decisions. The existing ROI
figures remain hypothetical scenarios. The PBIX file needs the new tables
imported manually; running Python updates its Excel source, not its visuals.

Verification: `python -m unittest discover -s tests -v`.
