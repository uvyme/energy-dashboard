from __future__ import annotations
from pathlib import Path
import time
import pandas as pd
import yfinance as yf

DATA = Path(__file__).resolve().parent.parent / "data"

PERIODS = {
    "ret_1d":  1,
    "ret_1w":  5,
    "ret_1m":  21,
    "ret_3m":  63,
    "ret_6m":  126,
    "ret_ytd": None,
    "ret_1y":  252,
}


def _load_universe() -> pd.DataFrame:
    eq = pd.read_csv(DATA / "universe.csv")
    macro = pd.read_csv(DATA / "macro_universe.csv")
    return eq, macro


def _download(tickers: list[str], period: str = "3y") -> pd.DataFrame:
    df = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="ticker",
    )
    return df


def _close_matrix(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        closes = {}
        for t in tickers:
            try:
                closes[t] = raw[t]["Close"]
            except Exception:
                continue
        return pd.DataFrame(closes).dropna(how="all")
    return raw["Close"].to_frame(name=tickers[0])


def _returns(close: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=close.columns)
    last = close.iloc[-1]
    for col, days in PERIODS.items():
        if days is None:
            ytd_start = close.loc[close.index.year == close.index[-1].year].iloc[0]
            out[col] = (last / ytd_start - 1.0) * 100
        else:
            if len(close) > days:
                out[col] = (last / close.iloc[-days - 1] - 1.0) * 100
            else:
                out[col] = pd.NA
    out["last_close"] = last
    out["high_52w"] = close.tail(252).max()
    out["low_52w"] = close.tail(252).min()
    out["pct_from_52w_high"] = (last / out["high_52w"] - 1.0) * 100
    out["pct_from_52w_low"] = (last / out["low_52w"] - 1.0) * 100
    vol_20 = close.pct_change().tail(20).std() * (252 ** 0.5) * 100
    out["vol_20d_ann"] = vol_20
    return out


def pull_all() -> dict[str, Path]:
    eq, macro = _load_universe()
    eq_tickers = eq["ticker"].tolist()
    macro_tickers = macro["ticker"].tolist()

    t0 = time.time()
    print(f"[prices] downloading {len(eq_tickers)} equities...")
    eq_raw = _download(eq_tickers, period="3y")
    eq_close = _close_matrix(eq_raw, eq_tickers)
    eq_close.to_parquet(DATA / "prices_equities.parquet")

    eq_ret = _returns(eq_close)
    eq_ret.index.name = "ticker"
    eq_ret = eq_ret.merge(eq.set_index("ticker"), left_index=True, right_index=True, how="left")
    eq_ret.to_parquet(DATA / "returns_equities.parquet")

    print(f"[prices] downloading {len(macro_tickers)} macro instruments...")
    macro_raw = _download(macro_tickers, period="5y")
    macro_close = _close_matrix(macro_raw, macro_tickers)
    macro_close.to_parquet(DATA / "prices_macro.parquet")

    print(f"[prices] done in {time.time()-t0:.1f}s")
    return {
        "prices_equities": DATA / "prices_equities.parquet",
        "returns_equities": DATA / "returns_equities.parquet",
        "prices_macro": DATA / "prices_macro.parquet",
    }


if __name__ == "__main__":
    pull_all()
