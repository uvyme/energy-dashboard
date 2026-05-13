# Energy Intel Dashboard

Free-data energy sector dashboard. No paid feeds.

## Data sources (all free)
- **yfinance** — equities, ETFs, futures, MOVE, VIX (15-min delayed, fine for investors)
- **FRED** — real yields, curve, dollar, Fed liquidity, HY spreads (no key needed via fredgraph.csv)
- **NY Fed** — ACM term premium (free CSV)
- **EIA** — oil flows, inventories (optional, set `EIA_API_KEY`; free key at eia.gov/opendata)
- **RSS** — 31 feeds across 6 tiers (wire / major / data / trade / curator / geo)

## Run locally

```bash
cd ~/claudecode/energy-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Refresh data (~85s, run after US close)
python refresh.py

# Launch dashboard
streamlit run app.py
```

Opens at http://localhost:8501.

## Deploy to Streamlit Community Cloud (free, public URL)

### 1. Push to GitHub

```bash
cd ~/claudecode/energy-dashboard
git init
git add .
git commit -m "initial commit"
# Create a new GitHub repo (private OK), then:
git remote add origin git@github.com:YOUR_USERNAME/energy-dashboard.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **New app** → pick your repo → main branch → `app.py`.
3. Under **Advanced settings → Secrets**, paste:
   ```toml
   password = "pick-a-strong-password"
   ```
   (Copy the format from `.streamlit/secrets.toml.example`.)
4. Click **Deploy**. App goes live in 2–3 minutes at `your-app-name.streamlit.app`.

### 3. Set up daily auto-refresh (GitHub Actions, free)

The workflow at `.github/workflows/refresh.yml` is already configured:
- Runs at **22:00 UTC** weekdays (after US close)
- Pulls fresh data, commits updated parquets back to the repo
- Streamlit Cloud auto-redeploys on each commit, so the live dashboard always shows last-close numbers

No setup needed — it activates the moment you push to GitHub. To trigger manually: GitHub repo → **Actions** tab → **Daily Data Refresh** → **Run workflow**.

### 4. Share with your dad

Send him:
- The URL: `your-app-name.streamlit.app`
- The password you set in step 2

That's it. He gets the dashboard, you get free daily refresh.

## Schedule local refresh (optional)

If you want a local cron in addition to the cloud workflow:

```cron
0 22 * * 1-5  cd ~/claudecode/energy-dashboard && .venv/bin/python refresh.py >> refresh.log 2>&1
```

## Files

```
data/
  universe.csv            12 sub-sectors, 96 tickers (clean energy excluded)
  macro_universe.csv      macro instruments for regime ratios
  fred_series.csv         FRED series to pull
  *.parquet               populated by refresh.py
pull/                     data fetchers (one file per source)
compute/                  ratios, regime classification, z-score ranking
app.py                    Streamlit dashboard (5 tabs)
refresh.py                orchestrator
.github/workflows/        daily cron via GitHub Actions
.streamlit/
  config.toml             dark theme settings
  secrets.toml.example    password template
```

## Edit the universe

Open `data/universe.csv`, add/remove rows. Sub-sector slug must match one in `app.py`'s `SUB` dict (or add a new one there). Next refresh picks it up.
