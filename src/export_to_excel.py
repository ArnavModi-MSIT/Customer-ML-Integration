"""Writes every processed table to one multi-sheet Excel workbook — the file Power BI reads from."""
import os
import pandas as pd

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "olist_analytics.xlsx"
)

SHEET_NAME_LIMIT = 31  # Excel's hard limit on sheet name length


def export_to_excel(tables, out_path=OUT_PATH, verbose=True):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for name, df in tables.items():
            sheet_name = name[:SHEET_NAME_LIMIT]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            if verbose:
                print(f"  wrote sheet '{sheet_name}': {len(df):,} rows x {len(df.columns)} cols")
    if verbose:
        print(f"✓ Excel workbook written to {out_path}")
    return out_path
