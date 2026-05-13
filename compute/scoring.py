from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

VALUATION = {
    "trailingPE":                  "lower",
    "forwardPE":                   "lower",
    "priceToBook":                 "lower",
    "priceToSalesTrailing12Months": "lower",
    "enterpriseToEbitda":          "lower",
    "enterpriseToRevenue":         "lower",
    "fcf_yield":                   "higher",
}

QUALITY = {
    "returnOnEquity":   "higher",
    "returnOnAssets":   "higher",
    "operatingMargins": "higher",
    "ebitdaMargins":    "higher",
    "debtToEquity":     "lower",
    "currentRatio":     "higher",
}

MOMENTUM = {
    "ret_1m":  "higher",
    "ret_3m":  "higher",
    "ret_6m":  "higher",
    "ret_1y":  "higher",
    "ret_ytd": "higher",
    "pct_from_52w_high": "higher",
}

SHAREHOLDER = {
    "dividendYield":  "higher",
    "fiveYearAvgDividendYield": "higher",
}


def _winsorize(s: pd.Series, p: float = 0.05) -> pd.Series:
    if s.dropna().empty:
        return s
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lower=lo, upper=hi)


def _zscore(s: pd.Series, direction: str) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    s = _winsorize(s)
    mu = s.mean()
    sd = s.std()
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    z = (s - mu) / sd
    if direction == "lower":
        z = -z
    return z


def _pillar_score(group: pd.DataFrame, spec: dict[str, str]) -> pd.Series:
    cols = [c for c in spec if c in group.columns]
    if not cols:
        return pd.Series(np.nan, index=group.index)
    z = pd.DataFrame({c: _zscore(group[c], spec[c]) for c in cols})
    return z.mean(axis=1)


def compute() -> Path:
    fund = pd.read_parquet(DATA / "fundamentals.parquet")
    rets = pd.read_parquet(DATA / "returns_equities.parquet")

    df = fund.join(rets[[c for c in rets.columns if c not in fund.columns]], how="left")

    pieces = []
    for sub, grp in df.groupby("sub_sector"):
        if sub == "etf_anchor":
            continue
        scored = grp.copy()
        scored["z_value"]   = _pillar_score(grp, VALUATION)
        scored["z_quality"] = _pillar_score(grp, QUALITY)
        scored["z_momentum"] = _pillar_score(grp, MOMENTUM)
        scored["z_yield"]   = _pillar_score(grp, SHAREHOLDER)
        scored["composite"] = (
            0.35 * scored["z_value"].fillna(0) +
            0.25 * scored["z_quality"].fillna(0) +
            0.30 * scored["z_momentum"].fillna(0) +
            0.10 * scored["z_yield"].fillna(0)
        )
        scored["rank_in_subsector"] = scored["composite"].rank(ascending=False, method="min")
        pieces.append(scored)

    out = pd.concat(pieces) if pieces else df
    out_path = DATA / "scored.parquet"
    out.to_parquet(out_path)
    print(f"[scoring] scored {len(out)} names across {out['sub_sector'].nunique()} sub-sectors")
    return out_path


if __name__ == "__main__":
    compute()
