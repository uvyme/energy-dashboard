"""Daily refresh: pull everything, compute everything, write parquets."""
from __future__ import annotations
import time
import sys
import traceback


def run():
    t0 = time.time()
    print("=" * 60)
    print("ENERGY DASHBOARD REFRESH")
    print("=" * 60)

    steps = [
        ("prices",       "pull.prices"),
        ("fundamentals", "pull.fundamentals"),
        ("macro",        "pull.macro"),
        ("eia",          "pull.eia"),
        ("news",         "pull.news"),
        ("ratios",       "compute.ratios"),
        ("scoring",      "compute.scoring"),
        ("heatmap",      "compute.heatmap"),
    ]

    failed = []
    for label, modname in steps:
        print(f"\n--- {label} ---")
        try:
            mod = __import__(modname, fromlist=["pull_all", "compute"])
            fn = getattr(mod, "pull_all", None) or getattr(mod, "compute", None)
            if fn is None:
                print(f"  no entry point in {modname}")
                continue
            fn()
        except Exception as e:
            print(f"  FAIL: {e}")
            traceback.print_exc()
            failed.append(label)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"DONE in {elapsed:.1f}s")
    if failed:
        print(f"Failed steps: {failed}")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    run()
