from __future__ import annotations
from pathlib import Path
import time
import io
import pandas as pd
from curl_cffi import requests as crequests

DATA = Path(__file__).resolve().parent.parent / "data"

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
NYFED_ACM_URL = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"


def _fetch_fred_series(series_id: str) -> pd.Series:
    url = FRED_URL.format(series=series_id)
    r = crequests.get(url, timeout=30, impersonate="chrome")
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]
    date_col = df.columns[0]
    val_col = df.columns[1]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    s = df.dropna().set_index(date_col)[val_col]
    s.name = series_id
    return s


def pull_fred() -> Path:
    series_df = pd.read_csv(DATA / "fred_series.csv")
    t0 = time.time()
    print(f"[fred] fetching {len(series_df)} series...")
    cols = {}
    for _, row in series_df.iterrows():
        sid = row["series_id"]
        try:
            s = _fetch_fred_series(sid)
            cols[sid] = s
            print(f"  {sid} ok ({len(s)} obs)")
        except Exception as e:
            print(f"  {sid} FAIL: {e}")
    out = pd.concat(cols, axis=1).sort_index()
    out_path = DATA / "fred.parquet"
    out.to_parquet(out_path)
    print(f"[fred] done in {time.time()-t0:.1f}s -> {out_path.name}")
    return out_path


def pull_acm_term_premium() -> Path | None:
    try:
        r = crequests.get(NYFED_ACM_URL, timeout=30, impersonate="chrome")
        r.raise_for_status()
        df = pd.read_excel(io.BytesIO(r.content))
        out = DATA / "nyfed_acm.parquet"
        df.to_parquet(out)
        print(f"[acm] saved {len(df)} rows -> {out.name}")
        return out
    except Exception as e:
        print(f"[acm] failed: {e}")
        return None


def pull_all() -> dict[str, Path | None]:
    return {
        "fred": pull_fred(),
        "acm": pull_acm_term_premium(),
    }


if __name__ == "__main__":
    pull_all()
