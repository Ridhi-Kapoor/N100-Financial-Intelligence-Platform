"""
Script to execute the Day 37 Cluster Profiling & Portfolio Statistics pipeline.

Generates:
1. output/cluster_profiles.csv
2. output/cluster_labels.csv
3. reports/correlation_heatmap.png
4. output/outlier_report.csv
5. output/portfolio_stats.csv
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.cluster_profiling import run_cluster_profiling_pipeline


def main():
    print("=" * 70)
    print("      NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("     DAY 37: CLUSTER PROFILING & PORTFOLIO STATISTICS")
    print("=" * 70)

    try:
        results = run_cluster_profiling_pipeline(PROJECT_ROOT)

        profiles_df = results["cluster_profiles"]
        outliers_df = results["outlier_report"]
        stats_df = results["portfolio_stats"]
        paths = results["output_paths"]

        print("\n--- 1. CLUSTER STATISTICAL PROFILES ---")
        print(profiles_df[["Cluster ID", "Cluster Name", "Number of Companies", "return_on_equity_pct_mean", "debt_to_equity_mean"]].to_string(index=False))

        print(f"\n--- 2. SECTOR OUTLIERS DETECTED (|Z| > 3): {len(outliers_df)} ---")
        if not outliers_df.empty:
            print(outliers_df[["Company ID", "Company Name", "Broad Sector", "KPI Name", "Z-score"]].head(10).to_string(index=False))

        print("\n--- 3. PORTFOLIO DESCRIPTIVE STATISTICS (FIRST 5 KPIS) ---")
        print(stats_df.head(5).to_string(index=False))

        print("\n" + "=" * 70)
        print("ALL PROFILING & STATISTICS ARTIFACTS GENERATED SUCCESSFULLY:")
        for name, pth in paths.items():
            print(f"  - {name:25s}: {pth}")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR running Cluster Profiling pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
