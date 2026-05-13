from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

RATIOS = {
    "oil_gold":     ("USO", "GLD"),
    "copper_gold":  ("COPX", "GLD"),
    "gld_tlt":      ("GLD", "TLT"),
    "energy_spy":   ("XLE", "SPY"),
    "natgas_oil":   ("UNG", "USO"),
    "silver_gold":  ("SLV", "GLD"),
}


def _percentile_rank(series: pd.Series, lookback: int = 756) -> float:
    tail = series.tail(lookback).dropna()
    if len(tail) < 30:
        return float("nan")
    last = tail.iloc[-1]
    return float((tail < last).mean() * 100)


def _slope(series: pd.Series, n: int = 60) -> float:
    tail = series.tail(n).dropna()
    if len(tail) < 5:
        return float("nan")
    x = np.arange(len(tail))
    y = tail.values
    return float(np.polyfit(x, y, 1)[0])


def compute() -> Path:
    prices = pd.read_parquet(DATA / "prices_macro.parquet")

    out_rows = []
    ratio_series = {}
    for name, (num, den) in RATIOS.items():
        if num not in prices or den not in prices:
            continue
        r = prices[num] / prices[den]
        ratio_series[name] = r
        last = r.dropna().iloc[-1] if not r.dropna().empty else float("nan")
        out_rows.append({
            "ratio": name,
            "numerator": num,
            "denominator": den,
            "last": last,
            "pct_3y":  _percentile_rank(r, 756),
            "pct_1y":  _percentile_rank(r, 252),
            "slope_60d": _slope(r, 60),
            "chg_1m":  (r.iloc[-1] / r.iloc[-21] - 1) * 100 if len(r) > 21 else float("nan"),
            "chg_3m":  (r.iloc[-1] / r.iloc[-63] - 1) * 100 if len(r) > 63 else float("nan"),
            "chg_ytd": ((r.iloc[-1] / r.loc[r.index.year == r.index[-1].year].iloc[0]) - 1) * 100
                       if not r.empty else float("nan"),
        })

    ratios_df = pd.DataFrame(out_rows).set_index("ratio")
    ratios_df.to_parquet(DATA / "ratios.parquet")

    series_df = pd.DataFrame(ratio_series).dropna(how="all")
    series_df.to_parquet(DATA / "ratio_series.parquet")
    print(f"[ratios] computed {len(ratios_df)} ratios")
    return DATA / "ratios.parquet"


if __name__ == "__main__":
    compute()
