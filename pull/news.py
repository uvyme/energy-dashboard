from __future__ import annotations
from pathlib import Path
import time
import urllib.parse as up
import pandas as pd
from curl_cffi import requests as crequests
from xml.etree import ElementTree as ET

DATA = Path(__file__).resolve().parent.parent / "data"

# Tier system — used by the dashboard to color-code by impact speed.
# wire     = sub-minute market-moving headlines
# major    = reliable mainstream desk reporting (Reuters / Bloomberg / WSJ / FT / CNBC / AP)
# trade    = sector trade press (operational + sub-sector specific)
# data     = official data releases (EIA, OPEC, IEA)
# curator  = personal research feeds aligned with your four-way framework
# geo      = geopolitics / MENA specific

def gnews(query: str) -> str:
    """Google News RSS search — works for paywalled sites since headlines are free."""
    q = up.quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


FEEDS = {
    # ============ WIRE / FAST IMPACT ============
    "ZeroHedge":            ("https://feeds.feedburner.com/zerohedge/feed",                          "wire"),
    "ForexLive":            ("https://www.forexlive.com/feed/",                                       "wire"),
    "Investing · Commodities":("https://www.investing.com/rss/news_25.rss",                           "wire"),
    "Investing · Forex":    ("https://www.investing.com/rss/news_1.rss",                              "wire"),
    "MarketWatch · Top":    ("https://feeds.marketwatch.com/marketwatch/topstories",                  "wire"),
    "MarketWatch · Markets":("https://feeds.marketwatch.com/marketwatch/marketpulse",                 "wire"),

    # ============ MAJOR NEWSROOMS ============
    "Reuters · Energy":     (gnews("site:reuters.com (oil OR OPEC OR Hormuz OR refinery OR tanker)"),   "major"),
    "Reuters · Commodities":(gnews("site:reuters.com (commodities OR crude OR gas OR uranium)"),         "major"),
    "Bloomberg · Energy":   (gnews("site:bloomberg.com (oil OR OPEC OR refinery OR tanker OR Hormuz)"),  "major"),
    "Bloomberg · Markets":  (gnews("site:bloomberg.com (Fed OR yields OR dollar OR liquidity)"),         "major"),
    "WSJ · Markets":        ("https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",             "major"),
    "WSJ · World":          ("https://feeds.content.dowjones.io/public/rss/RSSWorldNews",               "major"),
    "FT · Energy":          (gnews("site:ft.com (oil OR OPEC OR energy OR refinery)"),                  "major"),
    "CNBC · Energy":        ("https://www.cnbc.com/id/19836768/device/rss/rss.html",                    "major"),
    "CNBC · Markets":       ("https://www.cnbc.com/id/15839069/device/rss/rss.html",                    "major"),

    # ============ DATA / OFFICIAL ============
    "EIA Today In Energy":  ("https://www.eia.gov/rss/todayinenergy.xml",                                "data"),

    # ============ SECTOR TRADE PRESS ============
    "OilPrice":             ("https://oilprice.com/rss/main",                                            "trade"),
    "Hellenic Shipping":    ("https://www.hellenicshippingnews.com/feed/",                               "trade"),
    "Splash247":            ("https://splash247.com/feed/",                                              "trade"),
    "gCaptain":             ("https://gcaptain.com/feed/",                                               "trade"),
    "Rigzone":              ("https://www.rigzone.com/news/rss/rigzone_latest.aspx",                     "trade"),
    "Yahoo Energy":         ("https://finance.yahoo.com/rss/topstories",                                 "trade"),

    # ============ CURATORS (free Substack posts) ============
    "Capital Wars · Howell":("https://capitalwars.substack.com/feed",                                    "curator"),
    "Doomberg":             ("https://doomberg.substack.com/feed",                                       "curator"),
    "Concoda":              ("https://concoda.substack.com/feed",                                        "curator"),
    "Apricitas Econ":       ("https://www.apricitas.io/feed",                                            "curator"),
    "Lyn Alden":            ("https://www.lynalden.com/feed/",                                           "curator"),

    # ============ GEOPOLITICS / MENA ============
    "Al Jazeera":           ("https://www.aljazeera.com/xml/rss/all.xml",                                "geo"),
    "Times of Israel · MENA":(gnews("site:timesofisrael.com (Iran OR Hormuz OR Saudi OR UAE OR oil)"),   "geo"),
    "The National · UAE":   (gnews("site:thenationalnews.com (oil OR energy OR Iran OR OPEC)"),          "geo"),
    "Reuters · MENA Energy":(gnews("site:reuters.com (Iran OR Saudi OR UAE OR Hormuz OR Gulf) energy"),  "geo"),
}


def _parse_rss(name: str, url: str) -> list[dict]:
    try:
        r = crequests.get(url, timeout=15, impersonate="chrome")
        r.raise_for_status()
        # Some RSS sources return XML with BOM or namespaces — be forgiving
        content = r.content
        root = ET.fromstring(content)
        items = []
        # Standard RSS 2.0
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = (it.findtext("pubDate") or "").strip()
            if not title:
                continue
            items.append({"title": title, "link": link, "pubDate": pub})
        # Atom fallback
        if not items:
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title = (it.findtext("a:title", namespaces=ns) or "").strip()
                link_el = it.find("a:link", namespaces=ns)
                link = link_el.get("href") if link_el is not None else ""
                pub = (it.findtext("a:updated", namespaces=ns) or it.findtext("a:published", namespaces=ns) or "").strip()
                if not title:
                    continue
                items.append({"title": title, "link": link, "pubDate": pub})
        return items[:25]
    except Exception as e:
        print(f"[news] {name} fail: {str(e)[:80]}")
        return []


def pull_all() -> Path:
    t0 = time.time()
    rows: list[dict] = []
    counts: dict[str, int] = {}
    for name, (url, tier) in FEEDS.items():
        items = _parse_rss(name, url)
        counts[name] = len(items)
        for it in items:
            it["source"] = name
            it["tier"] = tier
            rows.append(it)

    df = pd.DataFrame(rows)
    if not df.empty:
        df["pubDate_parsed"] = pd.to_datetime(df["pubDate"], errors="coerce", utc=True)
        df = df.drop_duplicates(subset=["title"], keep="first")
        df = df.sort_values("pubDate_parsed", ascending=False, na_position="last")
        df = df[["source", "tier", "title", "link", "pubDate", "pubDate_parsed"]]

    out = DATA / "news.parquet"
    df.to_parquet(out)

    # Concise summary table
    ok = [k for k, v in counts.items() if v > 0]
    bad = [k for k, v in counts.items() if v == 0]
    print(f"[news] {len(df)} items in {time.time()-t0:.1f}s · {len(ok)}/{len(FEEDS)} feeds live")
    if bad:
        print(f"[news] dead feeds: {', '.join(bad)}")
    return out


if __name__ == "__main__":
    pull_all()
