"""Energy Intel — professional dashboard."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import uuid
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from compute.regime import classify

DATA = Path(__file__).resolve().parent / "data"

# ============================================================================
# THEME
# ============================================================================

C = {
    "bg":         "#0b0813",   # slightly purple-tinted black
    "surface":    "#14101f",
    "elev":       "#1c1730",
    "border":     "#2a2440",
    "text":       "#e8eaed",
    "text_sec":   "#9da3b3",
    "text_mut":   "#6a6f85",
    "accent":     "#a855f7",   # violet-500
    "accent_d":   "#7c3aed",   # violet-600 — for hover / borders
    "accent_l":   "#c084fc",   # violet-400 — for emphasis text
    "accent_rgb": "168,85,247",
    "green":      "#22c55e",
    "green_d":    "#15803d",
    "red":        "#ef4444",
    "red_d":      "#991b1b",
    "blue":       "#3b82f6",
    "cyan":       "#06b6d4",
    "yellow":     "#eab308",
}

SUB = {
    "integrated_majors":   "Integrated Majors",
    "large_cap_ep":        "Large-Cap E&P",
    "small_mid_ep":        "Small/Mid E&P",
    "refiners":            "Refiners",
    "crude_tankers":       "Crude Tankers",
    "product_tankers":     "Product Tankers",
    "lng_carriers":        "LNG / Infra",
    "midstream":           "Midstream",
    "oilfield_services":   "Oilfield Services",
    "offshore_drillers":   "Offshore Drillers",
    "fertilizers_nitrogen":"Fertilizers",
    "uranium_nuclear":     "Uranium / Nuclear",
    "coal":                "Coal",
    "solar":               "Solar",
    "wind_renewables":     "Wind / Renewables",
    "battery_lithium":     "Battery / Lithium",
    "hydrogen_fuelcell":   "Hydrogen",
    "etf_anchor":          "ETF Anchor",
}

DIVERGING = [
    [0.00, C["red_d"]],
    [0.25, C["red"]],
    [0.50, C["surface"]],
    [0.75, C["green"]],
    [1.00, C["green_d"]],
]

# Plotly template
pio.templates["dash"] = go.layout.Template(
    layout=dict(
        paper_bgcolor=C["bg"],
        plot_bgcolor=C["bg"],
        font=dict(family='-apple-system, "SF Pro Text", system-ui, sans-serif',
                  size=11, color=C["text"]),
        colorway=[C["accent"], C["blue"], C["green"], C["yellow"], C["red"], "#a855f7"],
        xaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                   zerolinecolor=C["border"], tickfont=dict(color=C["text_sec"], size=10),
                   showgrid=True),
        yaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                   zerolinecolor=C["border"], tickfont=dict(color=C["text_sec"], size=10),
                   showgrid=True),
        legend=dict(font=dict(color=C["text_sec"], size=10),
                    bgcolor="rgba(0,0,0,0)", bordercolor=C["border"]),
        margin=dict(l=48, r=24, t=36, b=44),
        hoverlabel=dict(bgcolor=C["elev"], bordercolor=C["border"],
                        font=dict(color=C["text"], family="monospace")),
    )
)
pio.templates.default = "dash"


# ============================================================================
# PAGE
# ============================================================================

st.set_page_config(page_title="Energy Intel", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------- Password gate (only if password is set in secrets) -----
try:
    _DASH_PASSWORD = st.secrets.get("password")
except Exception:
    _DASH_PASSWORD = None

if _DASH_PASSWORD:
    if not st.session_state.get("auth_ok"):
        st.markdown(f"""
        <style>
          .stApp {{ background: #0b0813; }}
          .auth-card {{
            max-width: 380px; margin: 8rem auto 0 auto;
            padding: 2rem 2rem 1.5rem 2rem;
            background: #14101f; border: 1px solid #2a2440;
            border-radius: 8px;
            box-shadow: 0 8px 40px rgba(0,0,0,0.4);
          }}
          .auth-title {{
            color: #e8eaed; font-size: 1.1rem; font-weight: 600;
            letter-spacing: -0.01em; margin: 0 0 0.5rem 0;
          }}
          .auth-title .accent {{ color: #a855f7; }}
          .auth-sub {{
            color: #6a6f85; font-size: 0.7rem;
            letter-spacing: 0.12em; text-transform: uppercase;
            margin-bottom: 1.5rem;
          }}
          #MainMenu, footer, header {{ visibility: hidden; }}
        </style>
        <div class="auth-card">
          <div class="auth-title">ENERGY INTEL <span class="accent">·</span> SIGN IN</div>
          <div class="auth-sub">Enter password to continue</div>
        </div>
        """, unsafe_allow_html=True)
        c = st.container()
        with c:
            l, m, r = st.columns([1, 2, 1])
            with m:
                pwd_in = st.text_input("Password", type="password",
                                        key="pwd_input", label_visibility="collapsed",
                                        placeholder="Password")
                if pwd_in:
                    if pwd_in == _DASH_PASSWORD:
                        st.session_state.auth_ok = True
                        st.rerun()
                    else:
                        st.error("Wrong password.")
        st.stop()

st.markdown(f"""
<style>
  /* base reset */
  .stApp {{ background: {C['bg']}; }}
  .block-container {{ padding-top: 1rem; padding-bottom: 2rem; max-width: 1700px; }}

  /* hide chrome */
  #MainMenu, footer, header {{ visibility: hidden; }}
  .stDeployButton {{ display: none; }}

  /* typography */
  body, .stMarkdown, p, label, span, div {{
    font-family: -apple-system, "SF Pro Display", "Inter", system-ui, sans-serif;
  }}
  .stMarkdown p {{ color: {C['text']}; }}

  h1 {{
    font-size: 1.25rem !important; font-weight: 600 !important;
    letter-spacing: -0.01em !important; color: {C['text']} !important;
    margin: 0 !important; padding: 0 !important;
  }}
  h2, h3 {{ margin-top: 0 !important; }}
  hr {{ border-color: {C['border']} !important; margin: 1rem 0 !important; }}

  /* tabs */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 0; border-bottom: 1px solid {C['border']};
    background: transparent;
  }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    padding: 0.5rem 1.5rem !important;
    color: {C['text_mut']} !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {C['accent']} !important;
    border-bottom-color: {C['accent']} !important;
  }}

  /* dataframe */
  .stDataFrame, .stDataFrame * {{ font-variant-numeric: tabular-nums; }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"] {{ font-size: 12px; }}

  /* widgets */
  .stMultiSelect [data-baseweb="select"],
  .stSelectbox [data-baseweb="select"] {{
    background: {C['surface']} !important;
    border-color: {C['border']} !important;
  }}
  .stMultiSelect span[data-baseweb="tag"] {{
    background: {C['elev']} !important;
    border: 1px solid {C['border']} !important;
  }}

  /* section labels (kicker) */
  .kicker {{
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.18em;
    text-transform: uppercase; color: {C['text_mut']};
    margin: 1.25rem 0 0.5rem 0;
    padding-left: 0.6rem;
    border-left: 2px solid {C['accent']};
    line-height: 1.1;
  }}
  .kicker-accent {{ color: {C['accent_l']}; }}

  /* header bar */
  .topbar {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.25rem 0 1rem 0;
    border-bottom: 1px solid {C['border']};
    margin-bottom: 1rem;
    position: relative;
  }}
  .topbar::after {{
    content: ""; position: absolute; bottom: -1px; left: 0;
    width: 120px; height: 1px;
    background: linear-gradient(90deg, {C['accent']}, transparent);
  }}
  .topbar-title {{
    font-size: 1.2rem; font-weight: 600; color: {C['text']};
    letter-spacing: -0.01em;
  }}
  .topbar-title .accent {{ color: {C['accent']}; }}
  .topbar-meta {{
    font-size: 0.7rem; color: {C['text_mut']};
    letter-spacing: 0.06em; text-transform: uppercase;
    font-variant-numeric: tabular-nums;
    display: inline-flex; align-items: center; gap: 0.5rem;
  }}
  .live-dot {{
    display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    background: {C['accent']};
    box-shadow: 0 0 0 0 rgba({C['accent_rgb']}, 0.7);
    animation: livePulse 2.2s infinite cubic-bezier(0.66, 0, 0, 1);
  }}
  @keyframes livePulse {{
    0%   {{ box-shadow: 0 0 0 0   rgba({C['accent_rgb']}, 0.6); }}
    70%  {{ box-shadow: 0 0 0 10px rgba({C['accent_rgb']}, 0); }}
    100% {{ box-shadow: 0 0 0 0   rgba({C['accent_rgb']}, 0); }}
  }}

  /* KPI cards */
  .kpi {{
    background: linear-gradient(180deg, {C['elev']} 0%, {C['surface']} 100%);
    border: 1px solid {C['border']};
    border-radius: 5px;
    padding: 0.85rem 1rem;
    height: 100%;
    position: relative;
    overflow: hidden;
  }}
  .kpi::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba({C['accent_rgb']}, 0.6), transparent);
  }}
  .kpi-label {{
    font-size: 0.62rem;
    text-transform: uppercase; letter-spacing: 0.14em;
    color: {C['text_mut']};
    margin-bottom: 0.4rem;
  }}
  .kpi-value {{
    font-size: 1.55rem; font-weight: 500;
    color: {C['text']}; line-height: 1;
    font-variant-numeric: tabular-nums;
    font-family: "SF Mono", Menlo, Consolas, monospace;
  }}
  .kpi-sub {{
    font-size: 0.72rem; color: {C['text_sec']};
    margin-top: 0.45rem;
    font-variant-numeric: tabular-nums;
  }}
  .kpi-up    {{ color: {C['green']}; }}
  .kpi-down  {{ color: {C['red']}; }}
  .kpi-flat  {{ color: {C['text_sec']}; }}

  /* regime pill */
  .pill {{
    display: inline-block;
    padding: 0.3rem 0.7rem;
    border-radius: 3px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: "SF Mono", Menlo, monospace;
  }}
  .pill-late-kali       {{ background: rgba(168,85,247,0.15); color: {C['accent']}; border: 1px solid {C['accent']}; }}
  .pill-spring          {{ background: rgba(34,197,94,0.15);  color: {C['green']};  border: 1px solid {C['green']}; }}
  .pill-late-cycle-oil  {{ background: rgba(239,68,68,0.15);  color: {C['red']};    border: 1px solid {C['red']}; }}
  .pill-mixed           {{ background: rgba(139,149,167,0.12); color: {C['text_sec']}; border: 1px solid {C['border']}; }}

  /* signal items */
  .signal {{
    padding: 0.5rem 0.85rem;
    background: {C['surface']};
    border-left: 2px solid {C['accent']};
    margin: 0.25rem 0;
    font-size: 0.82rem;
    color: {C['text']};
    border-radius: 0 3px 3px 0;
  }}

  /* news */
  .news-card {{
    padding: 0.55rem 0 0.55rem 0.75rem;
    border-bottom: 1px solid {C['border']};
    border-left: 2px solid transparent;
    margin-left: -0.75rem;
    transition: background 0.1s;
  }}
  .news-card:hover {{ background: rgba(168,85,247,0.04); }}
  .news-card.tier-wire    {{ border-left-color: {C['red']}; }}
  .news-card.tier-major   {{ border-left-color: {C['blue']}; }}
  .news-card.tier-data    {{ border-left-color: {C['green']}; }}
  .news-card.tier-curator {{ border-left-color: {C['accent']}; }}
  .news-card.tier-geo     {{ border-left-color: {C['yellow']}; }}
  .news-card.tier-trade   {{ border-left-color: {C['text_mut']}; }}

  .news-tier {{
    display: inline-block;
    font-size: 0.55rem;
    padding: 0.08rem 0.4rem;
    border-radius: 2px;
    margin-right: 0.4rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    font-family: "SF Mono", Menlo, monospace;
    vertical-align: middle;
  }}
  .tier-wire-bg    {{ background: rgba(239,68,68,0.12);   color: {C['red']}; }}
  .tier-major-bg   {{ background: rgba(59,130,246,0.12);  color: {C['blue']}; }}
  .tier-data-bg    {{ background: rgba(34,197,94,0.12);   color: {C['green']}; }}
  .tier-curator-bg {{ background: rgba(168,85,247,0.14);  color: {C['accent']}; }}
  .tier-geo-bg     {{ background: rgba(234,179,8,0.12);   color: {C['yellow']}; }}
  .tier-trade-bg   {{ background: rgba(139,149,167,0.12); color: {C['text_sec']}; }}

  .news-source {{
    display: inline-block;
    font-size: 0.65rem;
    padding: 0.08rem 0.45rem;
    background: {C['elev']};
    color: {C['text_sec']};
    border-radius: 2px;
    margin-right: 0.55rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
    vertical-align: middle;
  }}
  .news-time {{
    color: {C['text_mut']}; font-size: 0.7rem;
    font-variant-numeric: tabular-nums;
    margin-left: 0.55rem;
  }}
  .news-card a {{
    color: {C['text']} !important;
    text-decoration: none;
    font-size: 0.92rem;
    line-height: 1.4;
  }}
  .news-card a:hover {{ color: {C['accent']} !important; }}

  /* tier filter chips */
  .tier-legend {{
    display: flex; gap: 0.5rem; align-items: center;
    margin: 0.5rem 0 1rem 0;
    font-size: 0.7rem;
  }}
  .tier-legend-item {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    color: {C['text_sec']};
  }}
  .tier-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 1px;
  }}

  /* table polish */
  table {{ font-variant-numeric: tabular-nums; }}
  .stDataFrame [data-testid="StyledDataFrameDataCell"]:hover {{
    background: rgba({C['accent_rgb']}, 0.05) !important;
  }}

  /* footer */
  .footer {{
    margin-top: 3rem; padding-top: 1rem;
    border-top: 1px solid {C['border']};
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.65rem; color: {C['text_mut']};
    letter-spacing: 0.06em; text-transform: uppercase;
  }}
  .footer-l {{ color: {C['text_sec']}; }}
  .footer-r {{ color: {C['text_mut']}; }}

  /* scrollbar */
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-track {{ background: {C['bg']}; }}
  ::-webkit-scrollbar-thumb {{ background: {C['border']}; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {C['accent_d']}; }}

  /* widgets — selection focus */
  .stMultiSelect [data-baseweb="select"]:focus-within,
  .stSelectbox [data-baseweb="select"]:focus-within {{
    border-color: {C['accent']} !important;
    box-shadow: 0 0 0 1px {C['accent']} !important;
  }}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPERS
# ============================================================================

@st.cache_data(ttl=600)
def load(name: str) -> pd.DataFrame:
    p = DATA / f"{name}.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def fmt_pct(v, decimals=1, sign=True):
    if v is None or pd.isna(v):
        return "—"
    s = f"{v:+.{decimals}f}%" if sign else f"{v:.{decimals}f}%"
    return s


def fmt_num(v, decimals=2):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{decimals}f}"


def fmt_money(v):
    if v is None or pd.isna(v) or v == 0:
        return "—"
    abs_v = abs(v)
    if abs_v >= 1e12: return f"${v/1e12:.2f}T"
    if abs_v >= 1e9:  return f"${v/1e9:.2f}B"
    if abs_v >= 1e6:  return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def kpi_card(label: str, value: str, sub: str = "", direction: str = "flat"):
    cls = {"up": "kpi-up", "down": "kpi-down"}.get(direction, "kpi-flat")
    return f"""<div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub {cls}">{sub}</div>
    </div>"""


def regime_pill(state: str) -> str:
    cls_map = {
        "late_kali":            "pill-late-kali",
        "spring_confirmation":  "pill-spring",
        "late_cycle_oil":       "pill-late-cycle-oil",
        "mixed_transition":     "pill-mixed",
    }
    cls = cls_map.get(state, "pill-mixed")
    return f'<span class="pill {cls}">{state.replace("_", " ")}</span>'


def file_mtime(name: str) -> str:
    p = DATA / f"{name}.parquet"
    if not p.exists():
        return "—"
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


# ---- TradingView widget embeds --------------------------------------------

TV_BG    = "rgba(11, 8, 19, 1)"
TV_GRID  = "rgba(42, 36, 64, 0.35)"
TV_ACC   = "rgba(168, 85, 247, 1)"
TV_ACC_T = "rgba(168, 85, 247, 0.35)"


def tv_advanced(symbol: str, height: int = 620, interval: str = "W",
                compact: bool = False) -> str:
    """Advanced Chart via tv.js constructor — honors overrides and disabled_features."""
    cid = "tv_" + uuid.uuid4().hex[:10]
    overrides = {
        # candles
        "mainSeriesProperties.candleStyle.upColor":               "#a855f7",
        "mainSeriesProperties.candleStyle.downColor":             "#ffffff",
        "mainSeriesProperties.candleStyle.drawBorder":            True,
        "mainSeriesProperties.candleStyle.borderUpColor":         "#a855f7",
        "mainSeriesProperties.candleStyle.borderDownColor":       "#ffffff",
        "mainSeriesProperties.candleStyle.drawWick":              True,
        "mainSeriesProperties.candleStyle.wickUpColor":           "#a855f7",
        "mainSeriesProperties.candleStyle.wickDownColor":         "#ffffff",
        # hollow candles
        "mainSeriesProperties.hollowCandleStyle.upColor":         "#a855f7",
        "mainSeriesProperties.hollowCandleStyle.downColor":       "#ffffff",
        "mainSeriesProperties.hollowCandleStyle.borderUpColor":   "#a855f7",
        "mainSeriesProperties.hollowCandleStyle.borderDownColor": "#ffffff",
        "mainSeriesProperties.hollowCandleStyle.wickUpColor":     "#a855f7",
        "mainSeriesProperties.hollowCandleStyle.wickDownColor":   "#ffffff",
        # bars
        "mainSeriesProperties.barStyle.upColor":                  "#a855f7",
        "mainSeriesProperties.barStyle.downColor":                "#ffffff",
        # heikin ashi
        "mainSeriesProperties.haStyle.upColor":                   "#a855f7",
        "mainSeriesProperties.haStyle.downColor":                 "#ffffff",
        "mainSeriesProperties.haStyle.borderUpColor":             "#a855f7",
        "mainSeriesProperties.haStyle.borderDownColor":           "#ffffff",
        "mainSeriesProperties.haStyle.wickUpColor":               "#a855f7",
        "mainSeriesProperties.haStyle.wickDownColor":             "#ffffff",
        # pane chrome
        "paneProperties.background":                              "#0b0813",
        "paneProperties.backgroundType":                          "solid",
        "paneProperties.vertGridProperties.color":                "rgba(42,36,64,0.3)",
        "paneProperties.horzGridProperties.color":                "rgba(42,36,64,0.3)",
        "paneProperties.crossHairProperties.color":               "#a855f7",
        "scalesProperties.textColor":                             "#9da3b3",
        "scalesProperties.lineColor":                             "#2a2440",
    }
    cfg = {
        "autosize":             True,
        "symbol":               symbol,
        "interval":             interval,
        "timezone":             "Etc/UTC",
        "theme":                "dark",
        "style":                "1",
        "locale":               "en",
        "toolbar_bg":           "#0b0813",
        "enable_publishing":    False,
        "allow_symbol_change":  False,
        "hide_top_toolbar":     compact,
        "hide_side_toolbar":    compact,
        "save_image":           False,
        "calendar":             False,
        "withdateranges":       True,
        "container_id":         cid,
        "studies":              [],
        "disabled_features": [
            "create_volume_indicator_by_default",
            "volume_force_overlay",
            "header_symbol_search",
            "symbol_search_hot_key",
            "header_compare",
            "use_localstorage_for_settings",
        ],
        "overrides":            overrides,
    }
    # tv.js constructor — the ONE API path that honors all overrides
    return f"""
    <div id="{cid}" style="height:{height}px;width:100%;border:1px solid #2a2440;border-radius:6px;overflow:hidden;background:#0b0813;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
      new TradingView.widget({json.dumps(cfg)});
    </script>
    """


def tv_overview(symbol: str, title: str, height: int = 320) -> str:
    """Compact symbol-overview card with built-in log scale + area chart."""
    cfg = {
        "symbols": [[title, symbol]],
        "chartOnly": False,
        "width": "100%",
        "height": height - 4,
        "locale": "en",
        "colorTheme": "dark",
        "autosize": False,
        "showVolume": False,
        "showMA": False,
        "hideDateRanges": False,
        "hideMarketStatus": True,
        "hideSymbolLogo": True,
        "scalePosition": "right",
        "scaleMode": "Logarithmic",
        "fontFamily": "-apple-system, sans-serif",
        "fontSize": "10",
        "noTimeScale": False,
        "valuesTracking": "1",
        "changeMode": "price-and-percent",
        "chartType": "area",
        "lineWidth": 2,
        "lineColor":   TV_ACC,
        "topColor":    "rgba(168, 85, 247, 0.30)",
        "bottomColor": "rgba(168, 85, 247, 0.00)",
        "dateRanges": ["12m|1W", "60m|1W", "all|1M"],
        "isTransparent": True,
        "backgroundColor": "rgba(11, 8, 19, 0)",
    }
    return f"""
    <div style="height:{height}px;width:100%;border:1px solid #2a2440;border-radius:6px;overflow:hidden;background:#14101f;padding:0;">
      <div class="tradingview-widget-container" style="height:100%;width:100%;">
        <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
          {json.dumps(cfg)}
        </script>
      </div>
    </div>
    """


# Ratios deliberately chosen against Yuvraj's four-way confluence framework
# All use CFD/cash symbols — NYMEX/COMEX futures fail in TradingView free embed
TV_RATIOS = [
    ("Oil / Gold",       "TVC:USOIL/TVC:GOLD"),
    ("Copper / Gold",    "TVC:COPPER/TVC:GOLD"),
    ("GLD / TLT",        "AMEX:GLD/NASDAQ:TLT"),
    ("Energy / SPX",     "AMEX:XLE/AMEX:SPY"),
    ("NatGas / WTI",     "TVC:NATURALGAS/TVC:USOIL"),
    ("Brent / WTI",      "TVC:UKOIL/TVC:USOIL"),
]


def stock_symbol(ticker: str) -> str:
    """yfinance ticker → TradingView symbol. TV auto-resolves bare US tickers."""
    return ticker.replace("-", ".")  # BRK-A → BRK.A etc.


SECTOR_LABEL = {
    "integrated_majors":    "Integrated Majors",
    "large_cap_ep":         "Large-Cap E&P",
    "small_mid_ep":         "Small/Mid E&P",
    "refiners":             "Refiners",
    "crude_tankers":        "Crude Tankers",
    "product_tankers":      "Product Tankers",
    "lng_carriers":         "LNG / Infra",
    "midstream":            "Midstream",
    "oilfield_services":    "Oilfield Services",
    "offshore_drillers":    "Offshore Drillers",
    "fertilizers_nitrogen": "Fertilizers",
    "coal":                 "Coal",
}


# ============================================================================
# LOAD
# ============================================================================

ratios       = load("ratios")
ratio_series = load("ratio_series")
scored       = load("scored")
heatmap_df   = load("heatmap_subsector")
news         = load("news")
fred         = load("fred")
prices_eq    = load("prices_equities")
prices_macro = load("prices_macro")

state = classify() if not ratios.empty else {"state": "no_data", "notes": [],
                                              "oil_gold_pct": None, "copper_gold_pct": None, "gld_tlt_pct": None}

if scored.empty:
    st.error("No data — run `python refresh.py` first.")
    st.stop()


# ============================================================================
# HEADER
# ============================================================================

last_refresh = file_mtime("scored")
st.markdown(f"""
<div class="topbar">
  <div class="topbar-title">ENERGY INTEL <span class="accent">·</span> SECTOR DASHBOARD</div>
  <div class="topbar-meta">
    REGIME: {regime_pill(state['state'])}
    &nbsp;·&nbsp;
    <span class="live-dot"></span> LAST REFRESH {last_refresh}
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# TABS
# ============================================================================

tab_r, tab_h, tab_u, tab_m, tab_n = st.tabs([
    "Regime", "Heatmap", "Universe", "Macro", "Newsflow"
])


# ---------------------------------------------------------------- REGIME ----
with tab_r:
    st.markdown('<div class="kicker">Cycle Regime</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("State", state["state"].replace("_", " ").title(),
                             f"{len(state['notes'])} signal{'s' if len(state['notes'])!=1 else ''}",
                             "flat"),
                    unsafe_allow_html=True)
    with c2:
        og = state.get("oil_gold_pct")
        dirn = "down" if og is not None and og < 20 else ("up" if og is not None and og > 60 else "flat")
        st.markdown(kpi_card("OIL / GOLD", f"{og:.0f}" if og is not None else "—",
                             "3-yr percentile", dirn),
                    unsafe_allow_html=True)
    with c3:
        cg = state.get("copper_gold_pct")
        dirn = "down" if cg is not None and cg < 20 else ("up" if cg is not None and cg > 60 else "flat")
        st.markdown(kpi_card("COPPER / GOLD", f"{cg:.0f}" if cg is not None else "—",
                             "3-yr percentile", dirn),
                    unsafe_allow_html=True)
    with c4:
        gt = state.get("gld_tlt_pct")
        dirn = "up" if gt is not None and gt > 70 else ("flat")
        st.markdown(kpi_card("GLD / TLT", f"{gt:.0f}" if gt is not None else "—",
                             "debasement gauge", dirn),
                    unsafe_allow_html=True)

    st.markdown('<div class="kicker kicker-accent">Signals</div>', unsafe_allow_html=True)
    if state["notes"]:
        for n in state["notes"]:
            st.markdown(f'<div class="signal">{n}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal" style="border-color:#5a6478">No active signals.</div>',
                    unsafe_allow_html=True)

    # ---------- HERO: Gold/Silver ----------
    st.markdown('<div class="kicker">Gold / Silver · Weekly · Log Scale '
                '<span style="color:#c084fc;font-weight:400;letter-spacing:0.04em;text-transform:none">'
                '— monetary-metals stress gauge</span></div>',
                unsafe_allow_html=True)
    components.html(
        tv_advanced("OANDA:XAUUSD/OANDA:XAGUSD", height=640, interval="W"),
        height=660,
    )

    # ---------- GRID: cycle ratios (advanced chart per ratio) ----------
    st.markdown('<div class="kicker">Cycle Ratios · Weekly · Log Scale</div>',
                unsafe_allow_html=True)
    cols_per_row = 2
    for i in range(0, len(TV_RATIOS), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        for j, (name, sym) in enumerate(TV_RATIOS[i:i+cols_per_row]):
            with cols[j]:
                st.markdown(
                    f'<div style="font-size:0.72rem;letter-spacing:0.14em;'
                    f'text-transform:uppercase;color:#9da3b3;'
                    f'padding:0 0 0.35rem 0.1rem;">{name}</div>',
                    unsafe_allow_html=True,
                )
                components.html(
                    tv_advanced(sym, height=440, interval="W", compact=False),
                    height=460,
                )

    # ---------- Computed ratios table (percentile rank) ----------
    st.markdown('<div class="kicker">Computed Ratios · 3-Year Percentile Rank</div>',
                unsafe_allow_html=True)
    if not ratios.empty:
        rtab = ratios[["last", "pct_3y", "pct_1y", "chg_1m", "chg_3m", "chg_ytd"]].copy()
        rtab.columns = ["Last", "Pct 3Y", "Pct 1Y", "1M %", "3M %", "YTD %"]
        st.dataframe(
            rtab,
            use_container_width=True,
            column_config={
                "Last":   st.column_config.NumberColumn(format="%.3f"),
                "Pct 3Y": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100),
                "Pct 1Y": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100),
                "1M %":   st.column_config.NumberColumn(format="%+.2f%%"),
                "3M %":   st.column_config.NumberColumn(format="%+.2f%%"),
                "YTD %":  st.column_config.NumberColumn(format="%+.2f%%"),
            },
            height=260,
        )


# --------------------------------------------------------------- HEATMAP ----
with tab_h:

    # ------ Sub-sector matrix ------
    st.markdown('<div class="kicker">Sub-Sector Performance Matrix</div>', unsafe_allow_html=True)

    if not heatmap_df.empty:
        ret_cols = [c for c in ["ret_1d","ret_1w","ret_1m","ret_3m","ret_6m","ret_ytd","ret_1y"]
                    if c in heatmap_df.columns]
        labels = {"ret_1d":"1D","ret_1w":"1W","ret_1m":"1M","ret_3m":"3M",
                  "ret_6m":"6M","ret_ytd":"YTD","ret_1y":"1Y"}
        x_labels = [labels[c] for c in ret_cols]
        y_labels = [SUB.get(s, s) for s in heatmap_df.index.tolist()]
        z = heatmap_df[ret_cols].values

        text = [[f"{v:+.1f}" if pd.notna(v) else "" for v in row] for row in z]
        z_clip = np.clip(z, -30, 30)

        fig = go.Figure(go.Heatmap(
            z=z_clip, x=x_labels, y=y_labels,
            colorscale=DIVERGING, zmid=0, zmin=-30, zmax=30,
            text=text, texttemplate="%{text}",
            textfont=dict(family="SF Mono, monospace", size=11),
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:+.2f}%<extra></extra>",
            colorbar=dict(title="%", tickfont=dict(color=C["text_sec"], size=10),
                          outlinecolor=C["border"], thickness=10),
            xgap=2, ygap=2,
        ))
        fig.update_layout(height=520, margin=dict(l=160, r=20, t=20, b=40))
        fig.update_xaxes(side="top", tickfont=dict(size=11, color=C["text"]))
        fig.update_yaxes(tickfont=dict(size=11, color=C["text"]))
        st.plotly_chart(fig, use_container_width=True)

    # ------ SECTOR CHAMPIONS — top stock per sub-sector ------
    if not scored.empty:
        st.markdown('<div class="kicker">Sector Champions '
                    '<span style="color:#c084fc;font-weight:400;letter-spacing:0.04em;'
                    'text-transform:none">— best overall score per sub-sector</span></div>',
                    unsafe_allow_html=True)

        non_etf = scored[scored["sub_sector"] != "etf_anchor"].copy()
        champs = non_etf.sort_values("composite", ascending=False) \
                        .groupby("sub_sector").head(1) \
                        .sort_values("composite", ascending=False)

        cards_per_row = 4
        rows = [list(champs.iterrows())[i:i+cards_per_row]
                for i in range(0, len(champs), cards_per_row)]
        for row_items in rows:
            cols = st.columns(cards_per_row, gap="small")
            for col, (ticker, r) in zip(cols, row_items):
                mom = r.get("ret_1m", 0)
                mom_class = "kpi-up" if mom > 0 else ("kpi-down" if mom < 0 else "kpi-flat")
                mom_sign = "+" if mom > 0 else ""
                with col:
                    st.markdown(f"""
                    <div class="kpi" style="border-top: 2px solid {C['accent']};">
                      <div class="kpi-label">{SUB.get(r['sub_sector'], r['sub_sector'])}</div>
                      <div class="kpi-value" style="font-size:1.25rem;">{ticker}</div>
                      <div style="font-size:0.7rem;color:{C['text_sec']};
                                  margin-top:0.3rem;font-variant-numeric:tabular-nums;">
                        {str(r.get('shortName',''))[:24]}
                      </div>
                      <div class="kpi-sub {mom_class}" style="margin-top:0.4rem;">
                        1M {mom_sign}{mom:.1f}% &nbsp;·&nbsp; score {r.get('composite',0):+.2f}
                      </div>
                    </div>""", unsafe_allow_html=True)

    # ------ LEADERBOARDS — top 3 across 6 categories ------
    if not scored.empty:
        st.markdown('<div class="kicker">Leaderboards '
                    '<span style="color:#c084fc;font-weight:400;letter-spacing:0.04em;'
                    'text-transform:none">— top 3 by category</span></div>',
                    unsafe_allow_html=True)

        non_etf = scored[scored["sub_sector"] != "etf_anchor"].copy()

        def _leaders(df, col, ascending=False, n=3, label_col="composite_label"):
            d = df.dropna(subset=[col]).sort_values(col, ascending=ascending).head(n)
            return d[[col, "shortName", "sub_sector"]]

        categories = [
            ("Hottest · 1-Month %",      "ret_1m",            False, "{:+.1f}%"),
            ("Strongest YTD %",          "ret_ytd",           False, "{:+.1f}%"),
            ("Cheapest · Enterprise",    "enterpriseToEbitda", True, "{:.1f}x"),
            ("Highest Cash Yield",       "fcf_yield",         False, "{:.1f}%"),
            ("Best Momentum Score",      "z_momentum",        False, "{:+.2f}"),
            ("Best Overall Score",       "composite",         False, "{:+.2f}"),
        ]
        rows = [categories[i:i+3] for i in range(0, len(categories), 3)]
        for cat_row in rows:
            cols = st.columns(3, gap="small")
            for col, (title, metric, asc, fmt) in zip(cols, cat_row):
                if metric == "enterpriseToEbitda":
                    src = non_etf[non_etf["enterpriseToEbitda"] > 0]
                else:
                    src = non_etf
                top = src.dropna(subset=[metric]).sort_values(metric, ascending=asc).head(3)
                rows_html = ""
                for rank, (tk, rr) in enumerate(top.iterrows(), 1):
                    val = fmt.format(rr[metric])
                    name = str(rr.get("shortName", ""))[:24]
                    sect = SUB.get(rr["sub_sector"], rr["sub_sector"])
                    medal = ["#a855f7", "#c084fc", "#6a6f85"][rank-1]
                    rows_html += (
                        f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:center;padding:0.35rem 0;'
                        f'border-bottom:1px solid {C["border"]};">'
                        f'<div style="display:flex;align-items:center;gap:0.5rem;">'
                        f'<span style="color:{medal};font-weight:700;font-family:SF Mono,monospace;'
                        f'font-size:0.75rem;width:14px;">#{rank}</span>'
                        f'<div>'
                        f'<div style="font-family:SF Mono,monospace;color:{C["text"]};font-size:0.85rem;'
                        f'font-weight:600;">{tk}</div>'
                        f'<div style="color:{C["text_mut"]};font-size:0.65rem;">{sect}</div>'
                        f'</div></div>'
                        f'<div style="font-family:SF Mono,monospace;color:{C["accent_l"]};'
                        f'font-size:0.85rem;font-variant-numeric:tabular-nums;">{val}</div>'
                        f'</div>'
                    )
                with col:
                    st.markdown(f"""
                    <div class="kpi" style="padding:0.85rem 1rem;">
                      <div class="kpi-label">{title}</div>
                      <div style="margin-top:0.25rem;">{rows_html}</div>
                    </div>""", unsafe_allow_html=True)

    # ------ TOP 10 OVERALL ------
    if not scored.empty:
        st.markdown('<div class="kicker">Top 10 · Overall Score</div>',
                    unsafe_allow_html=True)
        non_etf = scored[scored["sub_sector"] != "etf_anchor"].copy()
        top10 = non_etf.dropna(subset=["composite"]).nlargest(10, "composite")
        top10 = top10.reset_index().rename(columns={"index":"Ticker","ticker":"Ticker"})
        top10["Sector"] = top10["sub_sector"].map(SUB)
        show = top10[["Ticker", "shortName", "Sector", "marketCap",
                      "ret_1m", "ret_ytd", "z_value", "z_quality", "z_momentum", "composite"]]
        show.columns = ["Ticker", "Company", "Sector", "Market Cap",
                        "1M %", "YTD %", "Value", "Quality", "Momentum", "Overall"]
        st.dataframe(
            show, use_container_width=True, hide_index=True, height=380,
            column_config={
                "Ticker":     st.column_config.TextColumn(width="small"),
                "Company":    st.column_config.TextColumn(width="medium"),
                "Sector":     st.column_config.TextColumn(width="small"),
                "Market Cap": st.column_config.NumberColumn(format="$%.0f", width="small"),
                "1M %":       st.column_config.NumberColumn(format="%+.1f%%"),
                "YTD %":      st.column_config.NumberColumn(format="%+.1f%%"),
                "Value":      st.column_config.NumberColumn(format="%+.2f",
                                  help="Standardized cheapness score within sub-sector. >0 = cheaper than peers"),
                "Quality":    st.column_config.NumberColumn(format="%+.2f",
                                  help="Standardized profitability + balance-sheet score within sub-sector"),
                "Momentum":   st.column_config.NumberColumn(format="%+.2f",
                                  help="Standardized recent-return score within sub-sector"),
                "Overall":    st.column_config.ProgressColumn(format="%+.2f",
                                  min_value=-3, max_value=3,
                                  help="Composite of value + quality + momentum + yield"),
            },
        )

    # ------ TREEMAP ------
    st.markdown('<div class="kicker">Universe Treemap '
                '<span style="color:#c084fc;font-weight:400;letter-spacing:0.04em;'
                'text-transform:none">— size = market cap, color = 1-month %</span></div>',
                unsafe_allow_html=True)
    if not scored.empty:
        tm = scored[(scored["marketCap"].notna()) & (scored["marketCap"] > 0)
                    & (scored["sub_sector"] != "etf_anchor")].copy()
        if not tm.empty:
            tm["ret_clip"] = tm["ret_1m"].clip(-25, 25)
            tm["Sub-sector"] = tm["sub_sector"].map(SUB)
            fig = px.treemap(
                tm.reset_index(),
                path=["Sub-sector", "ticker"],
                values="marketCap",
                color="ret_clip",
                color_continuous_scale=[(0, C["red_d"]), (0.5, C["surface"]), (1.0, C["green_d"])],
                color_continuous_midpoint=0,
                hover_data={"shortName": True, "marketCap": ":,.0f", "ret_1m": ":+.1f"},
            )
            fig.update_traces(
                root_color=C["bg"],
                marker=dict(line=dict(color=C["bg"], width=2)),
                textfont=dict(family="SF Mono, monospace", size=11, color=C["text"]),
                textposition="middle center",
            )
            fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_colorbar=dict(thickness=10,
                                                       tickfont=dict(color=C["text_sec"])))
            st.plotly_chart(fig, use_container_width=True)


# -------------------------------------------------------------- UNIVERSE ----
with tab_u:
    # ------ FILTERS ------
    st.markdown('<div class="kicker">Filters</div>', unsafe_allow_html=True)

    sub_opts = [s for s in scored["sub_sector"].dropna().unique() if s != "etf_anchor"]
    sub_opts = sorted(sub_opts, key=lambda x: SUB.get(x, x))
    pretty_opts = [SUB.get(s, s) for s in sub_opts]

    chosen_pretty = st.multiselect("Sector",
                                    pretty_opts, default=pretty_opts,
                                    key="univ_sub",
                                    help="Limit the universe to selected sub-sectors")
    reverse_map = {v: k for k, v in SUB.items()}
    chosen = [reverse_map.get(p, p) for p in chosen_pretty]
    view_pre = scored[scored["sub_sector"].isin(chosen)].copy()

    # Ratio sliders — wrap NaN handling
    def _safe_range(series, lo_q=0.02, hi_q=0.98, default=(0, 100)):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) < 5:
            return default
        return (float(s.quantile(lo_q)), float(s.quantile(hi_q)))

    f1, f2, f3, f4 = st.columns(4, gap="medium")

    with f1:
        mc_min, mc_max = _safe_range(view_pre["marketCap"] / 1e9, default=(0.1, 500))
        mc_min = max(0.05, mc_min)
        mc_range = st.slider("Market Cap (USD billions)",
                             min_value=0.0, max_value=float(round(mc_max + 50, -1)),
                             value=(0.0, float(round(mc_max + 50, -1))),
                             step=0.5,
                             help="Filter by total company size — sum of all shares × price")

    with f2:
        pe_min, pe_max = _safe_range(view_pre["trailingPE"], default=(0, 40))
        pe_max = min(80.0, max(40.0, pe_max + 5))
        pe_range = st.slider("Earnings Multiple (P/E)",
                             min_value=0.0, max_value=float(pe_max),
                             value=(0.0, float(pe_max)), step=0.5,
                             help="Price ÷ Earnings — how many years of current earnings to buy the company at today's price. Lower = cheaper")

    with f3:
        ev_min, ev_max = _safe_range(view_pre["enterpriseToEbitda"], default=(0, 25))
        ev_max = min(40.0, max(20.0, ev_max + 2))
        ev_range = st.slider("Enterprise Multiple (EV/EBITDA)",
                             min_value=0.0, max_value=float(ev_max),
                             value=(0.0, float(ev_max)), step=0.5,
                             help="Enterprise Value ÷ EBITDA — capital-structure-neutral valuation. Lower = cheaper")

    with f4:
        fcf_min, fcf_max = _safe_range(view_pre["fcf_yield"], default=(-10, 25))
        fcf_min = float(round(min(0, fcf_min - 2)))
        fcf_max = float(round(max(20, fcf_max + 2)))
        fcf_range = st.slider("Cash Yield % (FCF / Market Cap)",
                              min_value=fcf_min, max_value=fcf_max,
                              value=(fcf_min, fcf_max), step=0.5,
                              help="Free cash flow per dollar of market cap — how much real cash the business throws off relative to its price")

    g1, g2, g3 = st.columns([1, 1, 2], gap="medium")
    with g1:
        ret_min, ret_max = _safe_range(view_pre["ret_1m"], default=(-30, 30))
        ret_min = float(round(min(-50, ret_min - 5)))
        ret_max = float(round(max(50, ret_max + 5)))
        ret_range = st.slider("1-Month Return %",
                              min_value=ret_min, max_value=ret_max,
                              value=(ret_min, ret_max), step=1.0,
                              help="Total stock return over the last month")
    with g2:
        nan_keep = st.checkbox("Include missing data", value=True,
                                help="If unchecked, stocks with any missing ratio are filtered out")
    with g3:
        all_tickers = sorted(view_pre.index.tolist())
        focus_ticker = st.selectbox("Jump to ticker (optional)",
                                     options=[""] + all_tickers,
                                     index=0,
                                     help="Pre-select a stock to drill into below")

    # Apply filters
    def _in_range(s, lo, hi, allow_nan):
        s_num = pd.to_numeric(s, errors="coerce")
        mask = (s_num >= lo) & (s_num <= hi)
        if allow_nan:
            mask = mask | s_num.isna()
        return mask

    view = view_pre[
        _in_range(view_pre["marketCap"] / 1e9, mc_range[0], mc_range[1], nan_keep)
        & _in_range(view_pre["trailingPE"], pe_range[0], pe_range[1], nan_keep)
        & _in_range(view_pre["enterpriseToEbitda"], ev_range[0], ev_range[1], nan_keep)
        & _in_range(view_pre["fcf_yield"], fcf_range[0], fcf_range[1], nan_keep)
        & _in_range(view_pre["ret_1m"], ret_range[0], ret_range[1], nan_keep)
    ].copy()

    # Sparkline data — last 90 days of prices per ticker
    if not prices_eq.empty:
        spark_window = prices_eq.tail(90)
        def _spark(t):
            if t in spark_window.columns:
                s = spark_window[t].dropna()
                if len(s) > 1:
                    return s.tolist()
            return None
        view["trend"] = [_spark(t) for t in view.index]
    else:
        view["trend"] = None

    view["Sector"] = view["sub_sector"].map(SUB)
    view = view.reset_index().rename(columns={"index": "Ticker", "ticker": "Ticker"})
    view = view.sort_values(["sub_sector", "composite"], ascending=[True, False])

    display = view[[
        "Ticker", "shortName", "Sector", "marketCap", "trend",
        "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda", "fcf_yield",
        "returnOnEquity", "operatingMargins", "debtToEquity", "dividendYield",
        "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y",
        "z_value", "z_quality", "z_momentum", "composite", "rank_in_subsector",
    ]].copy()
    display.columns = [
        "Ticker", "Company", "Sector", "Size", "90D Trend",
        "P/E", "Fwd P/E", "Price/Book", "EV/EBITDA", "Cash Yield",
        "ROE", "Op Margin", "Leverage", "Dividend",
        "1M", "3M", "6M", "YTD", "1Y",
        "Value", "Quality", "Momentum", "Overall", "Rank",
    ]

    st.markdown(f'<div class="kicker">Universe '
                f'<span style="color:#c084fc;font-weight:400;letter-spacing:0.04em;'
                f'text-transform:none">— {len(display)} stocks · click row to drill in</span></div>',
                unsafe_allow_html=True)

    selection = st.dataframe(
        display, use_container_width=True, height=560, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        key="universe_table",
        column_config={
            "Ticker":     st.column_config.TextColumn("Ticker", width="small",
                              help="Exchange ticker symbol"),
            "Company":    st.column_config.TextColumn("Company", width="medium"),
            "Sector":     st.column_config.TextColumn("Sector", width="small",
                              help="Sub-sector within energy"),
            "Size":       st.column_config.NumberColumn("Size", format="$%.0f", width="small",
                              help="Market capitalization — total value of all company shares (USD)"),
            "90D Trend":  st.column_config.LineChartColumn("90D", width="small",
                              help="Stock price over the last 90 trading days"),
            "P/E":        st.column_config.NumberColumn("P/E", format="%.1f", width="small",
                              help="Price ÷ Earnings — years of current earnings to buy the company at today's price. Lower = cheaper"),
            "Fwd P/E":    st.column_config.NumberColumn("Fwd P/E", format="%.1f", width="small",
                              help="Price ÷ next year's estimated earnings"),
            "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f", width="small",
                              help="Price ÷ Book Value — multiple of accounting net worth"),
            "EV/EBITDA":  st.column_config.NumberColumn("EV/EBITDA", format="%.1f", width="small",
                              help="Enterprise Value ÷ EBITDA — capital-structure-neutral valuation"),
            "Cash Yield": st.column_config.NumberColumn("Cash Yld", format="%.1f%%", width="small",
                              help="Free Cash Flow ÷ Market Cap. How much real cash the business throws off relative to its price"),
            "ROE":        st.column_config.NumberColumn("ROE", format="%.1%%", width="small",
                              help="Return on Equity — profit per dollar of shareholder equity"),
            "Op Margin":  st.column_config.NumberColumn("Op Mgn", format="%.1%%", width="small",
                              help="Operating profit ÷ revenue — how much of each sales dollar becomes operating profit"),
            "Leverage":   st.column_config.NumberColumn("D/E", format="%.1f", width="small",
                              help="Total Debt ÷ Equity — higher = more leverage / risk"),
            "Dividend":   st.column_config.NumberColumn("Div %", format="%.1%%", width="small",
                              help="Annual dividend per dollar of share price"),
            "1M":         st.column_config.NumberColumn("1M %", format="%+.1f%%", width="small"),
            "3M":         st.column_config.NumberColumn("3M %", format="%+.1f%%", width="small"),
            "6M":         st.column_config.NumberColumn("6M %", format="%+.1f%%", width="small"),
            "YTD":        st.column_config.NumberColumn("YTD %", format="%+.1f%%", width="small"),
            "1Y":         st.column_config.NumberColumn("1Y %", format="%+.1f%%", width="small"),
            "Value":      st.column_config.NumberColumn("Val Z", format="%+.2f", width="small",
                              help="Standardized cheapness score within sub-sector. >0 = cheaper than peers"),
            "Quality":    st.column_config.NumberColumn("Qual Z", format="%+.2f", width="small",
                              help="Standardized profitability + balance-sheet score within sub-sector"),
            "Momentum":   st.column_config.NumberColumn("Mom Z", format="%+.2f", width="small",
                              help="Standardized recent-return score within sub-sector"),
            "Overall":    st.column_config.ProgressColumn("Score", format="%+.2f",
                              min_value=-3, max_value=3, width="small",
                              help="Composite z-score = 0.35·Value + 0.25·Quality + 0.30·Momentum + 0.10·Yield"),
            "Rank":       st.column_config.NumberColumn("Rank", format="%d", width="small",
                              help="Rank within sub-sector (1 = best Overall)"),
        },
    )

    # ------ DRILLDOWN ------
    selected_ticker = None
    if selection and getattr(selection, "selection", None):
        rows = selection.selection.rows
        if rows:
            selected_ticker = display.iloc[rows[0]]["Ticker"]
    if focus_ticker and not selected_ticker:
        selected_ticker = focus_ticker

    if selected_ticker:
        row = view[view["Ticker"] == selected_ticker]
        if not row.empty:
            r = row.iloc[0]
            sym = stock_symbol(selected_ticker)
            st.markdown(f"""
            <div class="kicker">Drilldown · {selected_ticker}
              <span style="color:{C['accent_l']};font-weight:400;letter-spacing:0.04em;
                           text-transform:none">— {str(r.get('shortName',''))} · {SUB.get(r['sub_sector'], r['sub_sector'])}</span>
            </div>
            """, unsafe_allow_html=True)

            # Three TradingView charts side by side
            cols = st.columns(3, gap="small")
            chart_height = 460
            charts = [
                (sym,                          f"{selected_ticker} · Price",
                 "Daily candles — purple up / white down"),
                (f"{sym}/AMEX:XLE",            f"{selected_ticker} / XLE",
                 "Relative to energy sector ETF — rising line = outperforming XLE"),
                (f"{sym}/TVC:USOIL",           f"{selected_ticker} / WTI",
                 "Relative to crude oil — rising line = outperforming oil price"),
            ]
            for col, (chart_sym, title, sub_title) in zip(cols, charts):
                with col:
                    st.markdown(
                        f'<div style="font-size:0.72rem;letter-spacing:0.14em;'
                        f'text-transform:uppercase;color:#9da3b3;'
                        f'padding:0 0 0.1rem 0.1rem;">{title}</div>'
                        f'<div style="font-size:0.65rem;color:{C["text_mut"]};'
                        f'padding:0 0 0.4rem 0.1rem;">{sub_title}</div>',
                        unsafe_allow_html=True,
                    )
                    components.html(
                        tv_advanced(chart_sym, height=chart_height, interval="D", compact=False),
                        height=chart_height + 20,
                    )
    else:
        st.markdown(
            f'<div style="padding:2rem 1rem;text-align:center;color:{C["text_mut"]};'
            f'font-size:0.9rem;border:1px dashed {C["border"]};border-radius:5px;margin-top:0.5rem;">'
            f'Click any row above to load 3 charts here — stock price, stock / XLE, stock / WTI.'
            f'</div>',
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------- MACRO ----
with tab_m:
    if fred.empty:
        st.info("No FRED data — run `python refresh.py`.")
    else:
        latest = fred.dropna(how="all")
        def _last(col):
            v = latest[col].dropna() if col in latest else pd.Series([])
            return (v.iloc[-1], v.iloc[-22] if len(v) > 22 else v.iloc[0]) if len(v) else (None, None)

        st.markdown('<div class="kicker">Headline Macro</div>', unsafe_allow_html=True)
        headline = [
            ("DFII10",       "Real 10Y", "%", 2),
            ("T10Y2Y",       "2s10s",    "bps", 0),
            ("BAMLH0A0HYM2", "HY OAS",   "bps", 0),
            ("DTWEXBGS",     "Broad $",  "",    2),
            ("DCOILWTICO",   "WTI",      "$",   2),
            ("DCOILBRENTEU", "Brent",    "$",   2),
        ]
        cols = st.columns(6)
        for i, (sid, lbl, unit, dec) in enumerate(headline):
            with cols[i]:
                cur, prior = _last(sid)
                if cur is None:
                    st.markdown(kpi_card(lbl, "—"), unsafe_allow_html=True)
                    continue
                if unit == "bps":
                    val_s = f"{cur*100:+.0f}"
                    delta = (cur - prior) * 100
                    delta_s = f"{delta:+.0f} bps · 1M"
                elif unit == "$":
                    val_s = f"${cur:.{dec}f}"
                    delta = (cur / prior - 1) * 100
                    delta_s = f"{delta:+.1f}% · 1M"
                elif unit == "%":
                    val_s = f"{cur:.{dec}f}%"
                    delta = cur - prior
                    delta_s = f"{delta:+.2f}pp · 1M"
                else:
                    val_s = f"{cur:.{dec}f}"
                    delta = (cur / prior - 1) * 100 if prior else 0
                    delta_s = f"{delta:+.2f}% · 1M"
                dirn = "up" if (cur - prior) > 0 else ("down" if (cur - prior) < 0 else "flat")
                st.markdown(kpi_card(lbl, val_s, delta_s, dirn), unsafe_allow_html=True)

        st.markdown('<div class="kicker">Time Series · 3-year window</div>', unsafe_allow_html=True)
        avail = [c for c in fred.columns if c in fred and fred[c].dropna().shape[0] > 100]
        defaults = [c for c in ["DFII10", "T10Y2Y", "BAMLH0A0HYM2"] if c in avail]
        sel = st.multiselect("", avail, default=defaults, label_visibility="collapsed", key="macro_sel")
        if sel:
            sub = fred[sel].dropna(how="all").tail(252 * 3)
            fig = go.Figure()
            for c in sub.columns:
                s = sub[c].dropna()
                fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines",
                                         name=c, line=dict(width=1.4)))
            fig.update_layout(height=420, legend=dict(orientation="h", y=1.08, x=0))
            st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------- NEWS ----
with tab_n:
    if news.empty:
        st.info("No news — run `python refresh.py`.")
    else:
        if "tier" not in news.columns:
            news["tier"] = "trade"

        TIER_LABEL = {
            "wire":    "Wire · Fast Impact",
            "major":   "Major Newsrooms",
            "data":    "Official Data",
            "curator": "Curators",
            "geo":     "Geopolitics · MENA",
            "trade":   "Sector Trade",
        }
        TIER_COLOR = {
            "wire": C["red"], "major": C["blue"], "data": C["green"],
            "curator": C["accent"], "geo": C["yellow"], "trade": C["text_sec"],
        }

        # ---------- KPI strip: counts per tier ----------
        st.markdown('<div class="kicker">Newsflow · 24-hour pulse</div>', unsafe_allow_html=True)
        now = pd.Timestamp.now(tz="UTC")
        recent = news.dropna(subset=["pubDate_parsed"]).copy()
        recent["age_h"] = (now - recent["pubDate_parsed"]).dt.total_seconds() / 3600
        last24 = recent[recent["age_h"] <= 24]

        cols = st.columns(6)
        for i, (tier, label) in enumerate(TIER_LABEL.items()):
            with cols[i]:
                n_total = (news["tier"] == tier).sum()
                n_24h   = (last24["tier"] == tier).sum()
                color = TIER_COLOR[tier]
                st.markdown(f"""
                <div class="kpi" style="border-top: 2px solid {color};">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-value">{n_24h}</div>
                  <div class="kpi-sub">{n_total} total · last 24h</div>
                </div>""", unsafe_allow_html=True)

        # ---------- filters ----------
        st.markdown('<div class="kicker">Filter</div>', unsafe_allow_html=True)
        fcol1, fcol2 = st.columns([1, 2])
        with fcol1:
            tiers_avail = [t for t in TIER_LABEL if t in news["tier"].values]
            tier_pretty = [TIER_LABEL[t] for t in tiers_avail]
            chosen_tier_pretty = st.multiselect("Tier", tier_pretty,
                                                 default=tier_pretty,
                                                 label_visibility="collapsed",
                                                 placeholder="Filter tiers…",
                                                 key="news_tier")
            chosen_tiers = [t for t, p in zip(tiers_avail, tier_pretty) if p in chosen_tier_pretty]
        with fcol2:
            sources = sorted(news[news["tier"].isin(chosen_tiers)]["source"].unique())
            pick = st.multiselect("Source", sources, default=sources,
                                  label_visibility="collapsed",
                                  placeholder="Filter sources…",
                                  key="news_pick")

        # legend
        legend_html = '<div class="tier-legend">'
        for tier in tiers_avail:
            color = TIER_COLOR[tier]
            label = TIER_LABEL[tier]
            legend_html += (f'<span class="tier-legend-item">'
                            f'<span class="tier-dot" style="background:{color};"></span>'
                            f'{label}</span>')
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

        # ---------- feed ----------
        view = news[news["tier"].isin(chosen_tiers) & news["source"].isin(pick)].head(200)

        st.markdown(f'<div class="kicker">Latest Headlines · {len(view)} of {len(news)}</div>',
                    unsafe_allow_html=True)

        for _, row in view.iterrows():
            time_s = ""
            if "pubDate_parsed" in row and pd.notna(row["pubDate_parsed"]):
                try:
                    delta = pd.Timestamp.now(tz="UTC") - row["pubDate_parsed"]
                    h = delta.total_seconds() / 3600
                    if h < 1:    time_s = f"{max(0, int(h*60))}m ago"
                    elif h < 24: time_s = f"{int(h)}h ago"
                    else:        time_s = f"{int(h/24)}d ago"
                except Exception:
                    time_s = ""
            tier = row.get("tier", "trade")
            st.markdown(
                f'<div class="news-card tier-{tier}">'
                f'<span class="news-tier tier-{tier}-bg">{tier}</span>'
                f'<span class="news-source">{row["source"]}</span>'
                f'<a href="{row["link"]}" target="_blank">{row["title"]}</a>'
                f'<span class="news-time">{time_s}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ============================================================================
# FOOTER
# ============================================================================

n_eq    = (scored["sub_sector"] != "etf_anchor").sum() if not scored.empty else 0
n_subs  = scored[scored["sub_sector"] != "etf_anchor"]["sub_sector"].nunique() if not scored.empty else 0
n_news  = len(news) if not news.empty else 0
n_feeds = news["source"].nunique() if not news.empty else 0

st.markdown(f"""
<div class="footer">
  <div class="footer-l">
    {n_eq} stocks · {n_subs} sub-sectors · {n_news} headlines from {n_feeds} feeds
  </div>
  <div class="footer-r">
    data: yfinance · fred · ny fed · eia · rss · all free
  </div>
</div>
""", unsafe_allow_html=True)
