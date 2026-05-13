from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pandas as pd
import yfinance as yf

DATA = Path(__file__).resolve().parent.parent / "data"

FIELDS = [
    "shortName", "longName", "sector", "industry", "country", "currency",
    "marketCap", "enterpriseValue",
    "trailingPE", "forwardPE", "pegRatio",
    "priceToBook", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue",
    "profitMargins", "operatingMargins", "grossMargins", "ebitdaMargins",
    "returnOnAssets", "returnOnEquity",
    "debtToEquity", "currentRatio", "quickRatio",
    "totalCash", "totalDebt", "totalRevenue", "ebitda",
    "freeCashflow", "operatingCashflow",
    "dividendYield", "payoutRatio", "fiveYearAvgDividendYield",
    "beta",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "fiftyDayAverage", "twoHundredDayAverage",
    "sharesOutstanding", "floatShares",
    "recommendationKey", "numberOfAnalystOpinions",
    "targetMeanPrice", "targetHighPrice", "targetLowPrice",
]


def _fetch_one(ticker: str) -> dict | None:
    try:
        info = yf.Ticker(ticker).info
        if not info or info.get("regularMarketPrice") is None and info.get("marketCap") is None:
            return None
        row = {"ticker": ticker}
        for f in FIELDS:
            row[f] = info.get(f)
        return row
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


def pull_all() -> Path:
    eq = pd.read_csv(DATA / "universe.csv")
    tickers = eq["ticker"].tolist()

    t0 = time.time()
    rows = []
    print(f"[fundamentals] fetching {len(tickers)} tickers...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_one, t): t for t in tickers}
        done = 0
        for fut in as_completed(futures):
            row = fut.result()
            if row:
                rows.append(row)
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(tickers)}")

    df = pd.DataFrame(rows).set_index("ticker")
    df = df.merge(eq.set_index("ticker")[["sub_sector"]], left_index=True, right_index=True, how="left")

    if "freeCashflow" in df and "marketCap" in df:
        df["fcf_yield"] = (df["freeCashflow"].astype("float64") / df["marketCap"].astype("float64")) * 100

    out = DATA / "fundamentals.parquet"
    df.to_parquet(out)
    print(f"[fundamentals] {len(df)} rows in {time.time()-t0:.1f}s -> {out.name}")
    return out


if __name__ == "__main__":
    pull_all()
