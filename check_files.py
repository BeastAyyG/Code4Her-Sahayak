#!/usr/bin/env python3
"""
Sahayak Safe Maps - File Size Checker

Analyzes vgm_streets.json and provides mobile deployment guidance.
ASCII-only output so it works cleanly on Windows terminals.
"""

from __future__ import annotations

import json
import os


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def check_geojson(filepath: str) -> None:
    print("=" * 60)
    print("SAHAYAK SAFE MAPS - FILE ANALYZER")
    print("=" * 60)

    if not os.path.exists(filepath):
        print(f"\nFile not found: {filepath}")
        print("Make sure vgm_streets.json is in the current directory.")
        return

    size_bytes = os.path.getsize(filepath)
    size_readable = format_size(size_bytes)

    print(f"\nFile: {filepath}")
    print(f"Size: {size_readable}")

    try:
        with open(filepath, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        features = data.get("features", [])
        lit_count = sum(1 for feature in features if feature.get("properties", {}).get("lit") == "yes")
        assumed_count = sum(1 for feature in features if feature.get("properties", {}).get("lit") == "assumed_yes")
        unlit_count = sum(1 for feature in features if feature.get("properties", {}).get("lit") == "no")

        print(f"Streets: {len(features)} features")
        print(f"Well-lit (mapped): {lit_count}")
        print(f"Likely lit (proxy): {assumed_count}")
        print(f"Unlit: {unlit_count}")
    except Exception as error:
        print(f"\nCould not parse GeoJSON: {error}")
        return

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if size_bytes < 1_000_000:
        print("\nExcellent. Your file is tiny and will load very quickly.")
        print("Recommendation: keep raw GeoJSON.")
    elif size_bytes < 5_000_000:
        print("\nGreat. Your file is a good size for mobile browsers.")
        print("Recommendation: keep raw GeoJSON.")
    elif size_bytes < 15_000_000:
        print("\nYour file is getting large for mobile browsers.")
        print("Recommendation: simplify with Mapshaper or convert to PMTiles.")
    else:
        print("\nYour file is large enough to hurt mobile performance.")
        print("Recommendation: convert to PMTiles.")

    print("\n" + "=" * 60)
    print("MOBILE PERFORMANCE ESTIMATE")
    print("=" * 60)

    if size_bytes < 1_000_000:
        print("Load time: under 1 second")
    elif size_bytes < 5_000_000:
        print("Load time: around 1-2 seconds")
    elif size_bytes < 15_000_000:
        print("Load time: around 3-5 seconds")
    else:
        print("Load time: 5+ seconds")

    print("\n" + "=" * 60)
    print("GITHUB PAGES COMPATIBILITY")
    print("=" * 60)
    print("GitHub Pages file limit: 100MB per file")
    print(f"Your file: {size_readable}")
    print("Within limit: yes" if size_bytes < 100_000_000 else "Within limit: no")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Raw GeoJSON is fine for the current dataset.")
    print("Total cost: $0")


if __name__ == "__main__":
    check_geojson("vgm_streets.json")
