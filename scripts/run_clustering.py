"""
Script to execute the Day 36 K-Means Financial Clustering pipeline.

Loads financial features, imputes sector medians, standardizes features,
fits K-Means (k=5), evaluates Elbow curve (k=2..10), derives dynamic cluster profile names,
saves reports/elbow_plot.png, and exports output/cluster_labels.csv.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.clustering import run_clustering_pipeline


def main():
    print("=" * 70)
    print("      NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("           DAY 36: K-MEANS FINANCIAL CLUSTERING")
    print("=" * 70)

    try:
        results = run_clustering_pipeline(PROJECT_ROOT)

        df_clusters = results["cluster_labels_df"]
        names_map = results["cluster_names"]
        inertias = results["inertias"]
        csv_path = results["output_csv"]
        elbow_path = results["elbow_plot"]

        print("\n--- 1. CLUSTER NAMES & ASSIGNMENTS SUMMARY ---")
        counts = df_clusters["Cluster ID"].value_counts().sort_index()
        for cid, count in counts.items():
            cname = names_map.get(cid, "N/A")
            print(f"  Cluster {cid}: {cname:30s} -> {count} companies")

        print("\n--- 2. ELBOW METHOD INERTIAS (k=2 to 10) ---")
        for k, inertia in inertias.items():
            selected_flag = " <-- Selected k=5" if k == 5 else ""
            print(f"  k = {k:2d}: Inertia = {inertia:10.2f}{selected_flag}")

        print("\n--- 3. SAMPLE OUTPUT (FIRST 10 COMPANIES) ---")
        print(df_clusters.head(10).to_string(index=False))

        print("\n" + "=" * 70)
        print("ALL CLUSTERING ARTIFACTS GENERATED SUCCESSFULLY:")
        print(f"  - Cluster Labels CSV: {csv_path}")
        print(f"  - Elbow Plot Image:  {elbow_path}")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR running K-Means Financial Clustering: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
