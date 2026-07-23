"""
Radar Chart Generation Analytics Module.

This module generates 8-axis financial performance radar (polar) charts for all companies
in the Nifty 100 dataset.

Axes:
- ROE
- ROCE
- Net Profit Margin
- Debt-to-Equity (Inverse score: lower D/E receives higher score)
- FCF Score
- PAT CAGR 5Y
- Revenue CAGR 5Y
- Composite Quality Score

Each chart plots the company's performance as a filled polygon and overlays:
- Peer Group Average as a dashed outline for companies assigned to a peer group.
- Nifty 100 Average as a dashed outline for standalone companies without a peer group.

All charts are saved as PNG files in 'reports/radar_charts/<company_id>_radar.png'.
"""

import logging
import math
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analytics.ratios import calculate_roce

# Define project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "radar_charts"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("radar_analytics")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(
        LOG_DIR / "radar_analytics.log", mode="a", encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

RADAR_METRIC_LABELS = [
    "ROE",
    "ROCE",
    "Net Profit Margin",
    "Debt-to-Equity",
    "FCF Score",
    "PAT CAGR 5Y",
    "Revenue CAGR 5Y",
    "Composite Quality Score",
]


def load_radar_data(
    db_path: Optional[Union[str, Path]] = None, year: Union[str, int] = "2024"
) -> pd.DataFrame:
    """
    Load company financials, calculate missing ROCE, and compute normalized 0-100 percentile scores for 8 radar metrics.

    Args:
        db_path: Path to nifty100.db.
        year: Target year for financial ratios.

    Returns:
        pd.DataFrame: Processed dataset with 0-100 score columns for the 8 metrics.
    """
    path_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    yr_str = str(year).strip()

    conn = sqlite3.connect(path_db)
    try:
        # 1. Base companies
        comps = pd.read_sql(
            "SELECT id, company_name, roce_percentage, roe_percentage FROM companies",
            conn,
        )
        comps["id"] = comps["id"].astype(str).str.strip()

        # 2. Financial ratios for target year (or latest available)
        fr = pd.read_sql(
            "SELECT company_id as id, return_on_equity_pct, net_profit_margin_pct, debt_to_equity, free_cash_flow_cr, pat_cagr_5yr, revenue_cagr_5yr, composite_quality_score FROM financial_ratios WHERE year = ?",
            conn,
            params=[yr_str],
        ).drop_duplicates(subset=["id"])
        fr["id"] = fr["id"].astype(str).str.strip()

        # If empty year, fallback to latest available year per company
        if fr.empty:
            fr = pd.read_sql(
                "SELECT company_id as id, return_on_equity_pct, net_profit_margin_pct, debt_to_equity, free_cash_flow_cr, pat_cagr_5yr, revenue_cagr_5yr, composite_quality_score FROM financial_ratios",
                conn,
            ).drop_duplicates(subset=["id"], keep="last")
            fr["id"] = fr["id"].astype(str).str.strip()

        # 3. Peer groups
        pg = pd.read_sql(
            "SELECT company_id as id, peer_group_name FROM peer_groups", conn
        ).drop_duplicates(subset=["id"])
        pg["id"] = pg["id"].astype(str).str.strip()

        # 4. P&L, Balance Sheet, Sectors for ROCE calculation
        pl = pd.read_sql(
            "SELECT company_id as id, profit_before_tax, interest FROM profitandloss WHERE year = ?",
            conn,
            params=[yr_str],
        ).drop_duplicates(subset=["id"])
        pl["id"] = pl["id"].astype(str).str.strip()

        bs = pd.read_sql(
            "SELECT company_id as id, equity_capital, reserves, borrowings FROM balancesheet WHERE year = ?",
            conn,
            params=[yr_str],
        ).drop_duplicates(subset=["id"])
        bs["id"] = bs["id"].astype(str).str.strip()

        sec = pd.read_sql(
            "SELECT company_id as id, broad_sector FROM sectors", conn
        ).drop_duplicates(subset=["id"])
        sec["id"] = sec["id"].astype(str).str.strip()

        # Merge all into single DataFrame
        merged = pd.merge(comps, fr, on="id", how="left")
        merged = pd.merge(merged, pg, on="id", how="left")
        merged = pd.merge(merged, pl, on="id", how="left")
        merged = pd.merge(merged, bs, on="id", how="left")
        merged = pd.merge(merged, sec, on="id", how="left")

        # Compute ROCE
        roce_list = []
        for _, r in merged.iterrows():
            try:
                pbt = (
                    float(r["profit_before_tax"])
                    if pd.notna(r.get("profit_before_tax"))
                    else 0.0
                )
                int_exp = float(r["interest"]) if pd.notna(r.get("interest")) else 0.0
                ebit = pbt + int_exp
                roce_res = calculate_roce(
                    ebit=ebit,
                    equity_capital=r.get("equity_capital"),
                    reserves=r.get("reserves"),
                    borrowings=r.get("borrowings"),
                    broad_sector=r.get("broad_sector"),
                )
                val = roce_res[0] if isinstance(roce_res, tuple) else roce_res
                if (val is None or math.isnan(val)) and pd.notna(
                    r.get("roce_percentage")
                ):
                    val = float(r["roce_percentage"])
                roce_list.append(val)
            except Exception:
                roce_list.append(
                    float(r["roce_percentage"])
                    if pd.notna(r.get("roce_percentage"))
                    else None
                )

        merged["roce"] = roce_list

        # Fallback for ROE if return_on_equity_pct is NaN but roe_percentage is present
        merged["roe"] = merged["return_on_equity_pct"].combine_first(
            merged["roe_percentage"]
        )

        # Compute 0-100 percentile scores for all 8 radar axes
        # Higher value -> Higher score (except Debt-to-Equity where lower value -> higher score)
        merged["ROE_score"] = (
            merged["roe"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["ROCE_score"] = (
            merged["roce"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["Net_Profit_Margin_score"] = (
            merged["net_profit_margin_pct"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        # Debt-to-Equity: Inverse ranking (lower D/E is better -> higher percentile score)
        merged["Debt_to_Equity_score"] = (
            merged["debt_to_equity"].rank(
                pct=True, ascending=False, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["FCF_Score"] = (
            merged["free_cash_flow_cr"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["PAT_CAGR_5Y_score"] = (
            merged["pat_cagr_5yr"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["Revenue_CAGR_5Y_score"] = (
            merged["revenue_cagr_5yr"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )
        merged["Composite_Quality_Score"] = (
            merged["composite_quality_score"].rank(
                pct=True, ascending=True, method="average", na_option="keep"
            )
            * 100.0
        )

        score_cols = [
            "ROE_score",
            "ROCE_score",
            "Net_Profit_Margin_score",
            "Debt_to_Equity_score",
            "FCF_Score",
            "PAT_CAGR_5Y_score",
            "Revenue_CAGR_5Y_score",
            "Composite_Quality_Score",
        ]

        # Fill NaNs in scores with neutral median 50.0
        for col in score_cols:
            merged[col] = merged[col].fillna(50.0)

        return merged
    finally:
        conn.close()


def generate_company_radar_chart(
    company_row: pd.Series,
    peer_averages: Dict[str, pd.Series],
    nifty_average: pd.Series,
    output_dir: Path,
) -> Path:
    """
    Generate and save a polar radar chart for a single company.

    Args:
        company_row: Series containing company metrics and scores.
        peer_averages: Dictionary mapping peer_group_name -> Series of 8 metric average scores.
        nifty_average: Series of Nifty 100 8 metric average scores.
        output_dir: Output directory Path for saving PNG.

    Returns:
        Path: Output PNG file path.
    """
    company_id = str(company_row["id"]).strip()
    company_name = str(company_row.get("company_name", company_id)).strip()
    peer_group = (
        str(company_row.get("peer_group_name")).strip()
        if pd.notna(company_row.get("peer_group_name"))
        else None
    )

    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    comp_values = [float(company_row[col]) for col in score_cols]
    comp_values += comp_values[:1]  # Close loop

    if peer_group and peer_group in peer_averages:
        ref_label = f"{peer_group} Avg"
        ref_scores = peer_averages[peer_group]
        ref_color = "#d62728"  # Crimson red for peer average
    else:
        ref_label = "Nifty 100 Avg"
        ref_scores = nifty_average
        ref_color = "#555555"  # Slate gray for market average

    ref_values = [float(ref_scores[col]) for col in score_cols]
    ref_values += ref_values[:1]  # Close loop

    # Angle calculation
    num_vars = len(RADAR_METRIC_LABELS)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    # Create Matplotlib Polar Plot
    fig, ax = plt.subplots(figsize=(8.5, 8.5), subplot_kw=dict(polar=True))

    # Background formatting
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Draw metric labels with padding
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(
        RADAR_METRIC_LABELS, fontsize=10, fontweight="bold", color="#111111"
    )

    # Draw radial y-ticks (0 to 100)
    ax.set_rlabel_position(22.5)
    plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="#666666", size=8)
    plt.ylim(0, 105)

    # Plot Company Polygon
    ax.plot(
        angles,
        comp_values,
        color="#1f77b4",
        linewidth=2.5,
        linestyle="-",
        label=f"{company_name} ({company_id})",
    )
    ax.fill(angles, comp_values, color="#1f77b4", alpha=0.32)

    # Plot Reference Overlay (Peer Avg or Nifty 100 Avg)
    ax.plot(
        angles,
        ref_values,
        color=ref_color,
        linewidth=2.0,
        linestyle="--",
        label=ref_label,
    )

    # Chart Title and Subtitle
    peer_sub = (
        f"Peer Group: {peer_group}"
        if peer_group
        else "Standalone Company (Benchmark: Nifty 100)"
    )
    title_text = f"{company_name} ({company_id})\n"
    ax.set_title(title_text, fontsize=14, fontweight="bold", pad=25, color="#111111")

    plt.suptitle(peer_sub, fontsize=10, fontstyle="italic", y=0.92, color="#444444")

    # Legend placement
    plt.legend(
        loc="upper right",
        bbox_to_anchor=(1.25, 1.12),
        frameon=True,
        facecolor="#ffffff",
        edgecolor="#cccccc",
        fontsize=9.5,
    )

    # Save chart PNG
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{company_id}_radar.png"
    plt.savefig(out_file, bbox_inches="tight", dpi=200)
    plt.close(fig)

    return out_file


def generate_all_radar_charts(
    db_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    year: Union[str, int] = "2024",
) -> List[Path]:
    """
    Generate radar charts for all companies in the dataset.

    Args:
        db_path: Path to SQLite DB.
        output_dir: Path to output directory for radar PNGs.
        year: Target financial year.

    Returns:
        List[Path]: List of generated image paths.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading dataset and computing 8 radar metric scores...")
    df = load_radar_data(db_path=db_path, year=year)

    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    # Pre-calculate Peer Group Averages
    peer_averages: Dict[str, pd.Series] = {}
    for pg, grp in df.groupby("peer_group_name"):
        if pd.notna(pg):
            peer_averages[str(pg).strip()] = grp[score_cols].mean()

    # Calculate Nifty 100 Market Average
    nifty_average = df[score_cols].mean()

    logger.info(
        f"Generating radar charts for {len(df)} companies into: {out_dir.resolve()}..."
    )

    generated_files = []
    for idx, row in df.iterrows():
        try:
            png_path = generate_company_radar_chart(
                company_row=row,
                peer_averages=peer_averages,
                nifty_average=nifty_average,
                output_dir=out_dir,
            )
            generated_files.append(png_path)
        except Exception as e:
            logger.error(
                f"Failed generating radar chart for company {row.get('id')}: {e}"
            )

    logger.info(f"Successfully generated {len(generated_files)} radar chart PNG files.")
    return generated_files


def main() -> None:
    """Main execution block."""
    logger.info("Starting Radar Chart Generation Pipeline...")
    generated = generate_all_radar_charts()
    logger.info(
        f"Pipeline complete! Generated {len(generated)} radar charts in 'reports/radar_charts/'."
    )


if __name__ == "__main__":
    main()
