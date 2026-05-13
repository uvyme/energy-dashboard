from __future__ import annotations
from pathlib import Path
import os
import time
import pandas as pd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"

EIA_KEY = os.environ.get("EIA_API_KEY", "").strip()

SERIES = {
    "crude_stocks_us":      "PET.WCESTUS1.W",
    "crude_production_us":  "PET.WCRFPUS2.W",
    "refining_utilization": "PET.WPULEUS3.W",
    "gasoline_stocks_us":   "PET.WGTSTUS1.W",
    "distillate_stocks_us": "PET.WDISTUS1.W",
    "crude_imports":        "PET.WCRIMUS2.W",
    "spr_stocks":           "PET.WCSSTUS1.W",
}


def _fetch_v2(series_id: str) -> pd.DataFrame:
    if not EIA_KEY:
        return pd.DataFrame()
    parts = series_id.split(".")
    if len(parts) < 2:
        return pd.DataFrame()
    url = (
        f"https://api.eia.gov/v2/seriesid/{series_id}?api_key={EIA_KEY}"
    )
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return pd.DataFrame()
    js = r.json()
    rows = js.get("response", {}).get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df


def pull_all() -> Path | None:
    if not EIA_KEY:
        print("[eia] EIA_API_KEY not set — skipping. Get one free at eia.gov/opendata")
        return None
    t0 = time.time()
    frames = {}
    for label, sid in SERIES.items():
        try:
            df = _fetch_v2(sid)
            if not df.empty:
                frames[label] = df
                print(f"  {label}: {len(df)} rows")
        except Exception as e:
            print(f"  {label} fail: {e}")
    if not frames:
        return None
    out = DATA / "eia.parquet"
    combined = pd.concat(frames, names=["series"]).reset_index()
    combined.to_parquet(out)
    print(f"[eia] done in {time.time()-t0:.1f}s")
    return out


if __name__ == "__main__":
    pull_all()
