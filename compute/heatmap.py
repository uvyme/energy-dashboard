from __future__ import annotations
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

RETURN_COLS = ["ret_1d", "ret_1w", "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y"]


def compute() -> Path:
    rets = pd.read_parquet(DATA / "returns_equities.parquet")
    rets = rets[rets["sub_sector"] != "etf_anchor"]

    grouped = rets.groupby("sub_sector")[RETURN_COLS].median()
    grouped["count"] = rets.groupby("sub_sector").size()

    grouped = grouped.sort_values("ret_1m", ascending=False)
    out_path = DATA / "heatmap_subsector.parquet"
    grouped.to_parquet(out_path)
    print(f"[heatmap] {len(grouped)} sub-sectors")
    return out_path


if __name__ == "__main__":
    compute()
