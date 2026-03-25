"""Consistency checks for the saved MahaKhumb experiment outputs."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

RESULT_PKL = Path("qaoa_results.pkl")
REPORT_JSON = Path("sprint_report.json")


def main() -> None:
    with RESULT_PKL.open("rb") as handle:
        result_data = pickle.load(handle)
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    cluster_results = result_data["cluster_results"]
    report_zones = {int(row["zone"]): row for row in report["zones"]}

    for cid, cluster in cluster_results.items():
        row = report_zones[cid]
        optimal_objective = float(cluster["optimal_objective"])
        exact_objective = float(cluster["exact"]["objective"])
        if abs(optimal_objective - exact_objective) > 1e-6:
            raise SystemExit(f"Exact solver mismatch on cluster {cid}: {optimal_objective} vs {exact_objective}")
        if abs(float(row["optimal_objective"]) - optimal_objective) > 1e-6:
            raise SystemExit(f"Report optimal mismatch on cluster {cid}")
        report_qaoa = float(row["qaoa_objective"])
        cluster_qaoa = float(cluster["qaoa"]["objective"])
        if report_qaoa != cluster_qaoa and abs(report_qaoa - cluster_qaoa) > 1e-6:
            raise SystemExit(f"Report QAOA mismatch on cluster {cid}")

    print("Validation passed")


if __name__ == "__main__":
    main()
