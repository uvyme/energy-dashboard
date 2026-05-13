from __future__ import annotations
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def classify() -> dict:
    """Cycle-aware regime classification using ratio percentiles.

    late_kali: OIL/GOLD bottom decile (Howell-style winter setup)
    spring_confirmation: OIL/GOLD AND COPPER/GOLD both rising from low base
    debasement: GLD/TLT in upper quintile and trending
    mixed_transition: ambiguous — ratios pointing different directions
    """
    ratios = pd.read_parquet(DATA / "ratios.parquet")

    def get(name, col):
        if name not in ratios.index:
            return None
        return ratios.loc[name, col]

    og_pct = get("oil_gold", "pct_3y")
    cg_pct = get("copper_gold", "pct_3y")
    gt_pct = get("gld_tlt", "pct_3y")
    og_slope = get("oil_gold", "slope_60d")
    cg_slope = get("copper_gold", "slope_60d")

    state = "mixed_transition"
    notes = []

    if og_pct is not None and og_pct < 15:
        state = "late_kali"
        notes.append(f"OIL/GOLD at {og_pct:.0f}th pct — late-Kondratiev Winter signal")
        if og_slope and og_slope > 0 and cg_slope and cg_slope > 0:
            state = "spring_confirmation"
            notes.append("Both OIL/GOLD and COPPER/GOLD slopes positive — Spring confirmation forming")
    elif og_pct is not None and og_pct > 80:
        state = "late_cycle_oil"
        notes.append(f"OIL/GOLD at {og_pct:.0f}th pct — late-cycle commodity")

    if gt_pct is not None and gt_pct > 80:
        notes.append(f"GLD/TLT at {gt_pct:.0f}th pct — debasement regime active")

    if cg_pct is not None and cg_pct < 20:
        notes.append(f"COPPER/GOLD at {cg_pct:.0f}th pct — growth-weak")
    elif cg_pct is not None and cg_pct > 70:
        notes.append(f"COPPER/GOLD at {cg_pct:.0f}th pct — growth-strong")

    return {
        "state": state,
        "notes": notes,
        "oil_gold_pct": og_pct,
        "copper_gold_pct": cg_pct,
        "gld_tlt_pct": gt_pct,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(classify(), indent=2, default=str))
