"""
Screener Presets Module.

This module defines and implements six predefined stock screening presets:
1. Quality Compounder - High returns, strong margins, low leverage, positive FCF.
2. Value Pick - Low P/E, low P/B, decent ROE, reasonable debt.
3. Growth Accelerator - Strong revenue/earnings CAGR 5Y and high profitability.
4. Dividend Champion - High dividend yield, consistent profits, safe leverage.
5. Debt-Free Blue Chip - Large market cap, zero/near-zero debt, solid ROE.
6. Turnaround Watch - Declining Debt-to-Equity YoY, profitable and stable.

It also implements a robust 0-100 sector-relative composite quality score based on:
- Profitability (35%): ROE (15%), ROCE (10%), NPM (10%)
- Cash Quality (30%): FCF CAGR 5Y (15%), CFO/PAT Ratio (10%), FCF Positive Flag (5%)
- Growth (20%): Revenue CAGR 5Y (10%), PAT CAGR 5Y (10%)
- Leverage (15%): Debt-to-Equity Score (10%, lower is better), Interest Coverage Score (5%, higher is better, debt-free gets 100)
"""

import logging
from pathlib import Path
from typing import Dict, Any, Union
import pandas as pd
import numpy as np

from src.screener.engine import (
    load_screener_data,
    apply_screener_filters,
    is_debt_free,
)
from src.analytics.cagr import calculate_cagr

logger = logging.getLogger("screener_presets")
logger.setLevel(logging.INFO)

# Define configurations for presets that can be directly mapped to the engine
PRESET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "quality_compounder": {
        "filters": {
            "ROE": {"min": 15.0},
            "Debt-to-Equity": {"max": 0.5},
            "Free Cash Flow": {"min": 0.0},
            "Operating Profit Margin": {"min": 12.0},
            "Interest Coverage Ratio": {"min": 3.0},
        }
    },
    "value_pick": {
        "filters": {
            "P/E": {"max": 35.0},
            "P/B": {"max": 5.0},
            "ROE": {"min": 12.0},
            "Debt-to-Equity": {"max": 1.2},
        }
    },
    "growth_accelerator": {
        "filters": {
            "Revenue CAGR 5Y": {"min": 12.0},
            "PAT CAGR 5Y": {"min": 12.0},
            "ROE": {"min": 12.0},
            "Operating Profit Margin": {"min": 10.0},
        }
    },
    "dividend_champion": {
        "filters": {
            "Dividend Yield": {"min": 2.0},
            "ROE": {"min": 10.0},
            "Debt-to-Equity": {"max": 1.2},
        }
    },
    "debt_free_blue_chip_base": {
        "filters": {"Market Cap": {"min": 20000.0}, "ROE": {"min": 12.0}}
    },
    "turnaround_watch_base": {
        "filters": {"ROE": {"min": 10.0}, "Net Profit": {"min": 100.0}}
    },
}


def load_and_score_data(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """
    Load data from nifty100.db and compute a 0-100 composite quality score for all companies.

    The score uses sector-relative winsorized normalization for 10 financial metrics:
    - ROE (15%), ROCE (10%), NPM (10%)
    - FCF CAGR 5Y (15%), CFO/PAT Ratio (10%), FCF Positive Flag (5%)
    - Revenue CAGR 5Y (10%), PAT CAGR 5Y (10%)
    - Debt-to-Equity (10%, lower is better), Interest Coverage (5%, debt-free = 100)
    """
    # 1. Load full database to support 5-year calculations (e.g. FCF CAGR from 2019 to 2024)
    df_all = load_screener_data(db_path)

    target_year_str = str(year).strip()
    df_target = df_all[df_all["year"] == target_year_str].copy()
    if df_target.empty:
        logger.warning(f"No records found for target year '{year}' in database.")
        return df_target

    # Group all data by company to build historical metrics
    fcf_history = (
        df_all[df_all["year"] == str(int(year) - 5)]
        .set_index("company_id")["free_cash_flow_cr"]
        .to_dict()
    )
    de_history = (
        df_all[df_all["year"] == str(int(year) - 1)]
        .set_index("company_id")["debt_to_equity"]
        .to_dict()
    )

    # Compute dynamic metrics for the target year
    fcf_cagrs = []
    cfo_pat_ratios = []
    fcf_pos_flags = []
    de_declined = []

    for _, row in df_target.iterrows():
        comp_id = row["company_id"]

        # A. FCF CAGR 5Y
        fcf_curr = row.get("free_cash_flow_cr")
        fcf_prev = fcf_history.get(comp_id)

        cagr_val = None
        if pd.notna(fcf_curr) and fcf_prev is not None and pd.notna(fcf_prev):
            val, flag = calculate_cagr(fcf_prev, fcf_curr, 5)
            if val is not None:
                cagr_val = val
            else:
                # Handle non-calculable CAGR with proxy values
                if flag == "TURNAROUND":
                    cagr_val = 10.0
                elif flag == "DECLINE_TO_LOSS":
                    cagr_val = -15.0
                elif flag == "BOTH_NEGATIVE":
                    cagr_val = -25.0
                else:
                    cagr_val = 0.0
        else:
            cagr_val = 0.0
        fcf_cagrs.append(cagr_val)

        # B. CFO/PAT Ratio
        cfo_pat_5y = row.get(
            "composite_quality_score"
        )  # Already computed 5y average in DB
        if pd.notna(cfo_pat_5y):
            cfo_pat_ratios.append(cfo_pat_5y)
        else:
            cfo = row.get("cash_from_operations_cr")
            pat = row.get("net_profit")
            if pd.notna(cfo) and pd.notna(pat) and pat != 0.0:
                cfo_pat_ratios.append(cfo / pat)
            else:
                cfo_pat_ratios.append(np.nan)

        # C. FCF Positive Flag
        fcf_pos_flags.append(1.0 if (pd.notna(fcf_curr) and fcf_curr > 0.0) else 0.0)

        # D. YoY D/E Decline
        de_curr = row.get("debt_to_equity")
        de_prev = de_history.get(comp_id)
        if pd.notna(de_curr) and de_prev is not None and pd.notna(de_prev):
            de_declined.append(de_curr < de_prev)
        else:
            de_declined.append(False)

    df_target["fcf_cagr_5yr"] = fcf_cagrs
    df_target["cfo_pat_ratio"] = cfo_pat_ratios
    df_target["fcf_positive_flag"] = fcf_pos_flags
    df_target["de_declined_yoy"] = de_declined

    # 2. Configure metrics and weights
    metrics_config = {
        "return_on_equity_pct": {"lower_is_better": False, "weight": 0.15},
        "roce_percentage": {"lower_is_better": False, "weight": 0.10},
        "net_profit_margin_pct": {"lower_is_better": False, "weight": 0.10},
        "fcf_cagr_5yr": {"lower_is_better": False, "weight": 0.15},
        "cfo_pat_ratio": {"lower_is_better": False, "weight": 0.10},
        "fcf_positive_flag": {"lower_is_better": False, "weight": 0.05},
        "revenue_cagr_5yr": {"lower_is_better": False, "weight": 0.10},
        "pat_cagr_5yr": {"lower_is_better": False, "weight": 0.10},
        "debt_to_equity": {"lower_is_better": True, "weight": 0.10},
        "interest_coverage": {"lower_is_better": False, "weight": 0.05},
    }

    # Pre-fill NaNs in metrics globally with median to avoid NaN propagation
    for col in metrics_config:
        if col in df_target.columns:
            median_val = df_target[col].median()
            if pd.isna(median_val):
                median_val = 0.0
            df_target[col] = df_target[col].fillna(median_val)
        else:
            df_target[col] = 0.0

    # Compute global P10 and P90 bounds
    global_bounds = {}
    for col in metrics_config:
        global_bounds[col] = {
            "p10": df_target[col].quantile(0.1),
            "p90": df_target[col].quantile(0.9),
        }

    # Helper to winsorize and scale a series
    def scale_group_series(
        series: pd.Series, col_name: str, lower_is_better: bool
    ) -> pd.Series:
        """Winsorize and scale a series to 0-100 score."""
        n_elements = len(series)
        p10 = series.quantile(0.1)
        p90 = series.quantile(0.9)

        # Fall back to global if group size < 5 or p10 == p90
        if n_elements < 5 or p10 == p90:
            p10 = global_bounds[col_name]["p10"]
            p90 = global_bounds[col_name]["p90"]

        if p90 > p10:
            winsorized = series.clip(lower=p10, upper=p90)
            scaled = (winsorized - p10) / (p90 - p10) * 100.0
            if lower_is_better:
                scaled = 100.0 - scaled
            return scaled
        else:
            return pd.Series(50.0, index=series.index)

    # Clean sector names
    df_target["broad_sector_clean"] = df_target["broad_sector"].fillna("Other")

    # Scale each metric sector-relatively
    scaled_scores = {}
    for col, config in metrics_config.items():
        lower_is_better = config["lower_is_better"]
        col_scaled = pd.Series(0.0, index=df_target.index)

        for sector, grp in df_target.groupby("broad_sector_clean"):
            if col == "interest_coverage":
                # Special Interest Coverage Logic: Debt-Free gets 100.0 directly
                df_mask = grp.apply(is_debt_free, axis=1)
                non_df_grp = grp[~df_mask]

                scaled_vals = pd.Series(100.0, index=grp.index)
                if not non_df_grp.empty:
                    scaled_non_df = scale_group_series(
                        non_df_grp[col], col, lower_is_better
                    )
                    scaled_vals.update(scaled_non_df)
                col_scaled.update(scaled_vals)
            else:
                scaled_vals = scale_group_series(grp[col], col, lower_is_better)
                col_scaled.update(scaled_vals)

        scaled_scores[f"{col}_score"] = col_scaled
        df_target[f"{col}_score"] = col_scaled

    # Calculate weighted composite score
    composite_score = pd.Series(0.0, index=df_target.index)
    for col, config in metrics_config.items():
        composite_score += df_target[f"{col}_score"] * config["weight"]

    # Overwrite the original composite_quality_score column
    df_target["composite_quality_score"] = composite_score
    return df_target


# --- Preset Filter Wrapper Functions ---


def apply_quality_compounder_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Quality Compounder preset filters."""
    return apply_screener_filters(df, PRESET_CONFIGS["quality_compounder"])


def apply_value_pick_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Value Pick preset filters."""
    return apply_screener_filters(df, PRESET_CONFIGS["value_pick"])


def apply_growth_accelerator_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Growth Accelerator preset filters."""
    return apply_screener_filters(df, PRESET_CONFIGS["growth_accelerator"])


def apply_dividend_champion_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Dividend Champion preset filters."""
    return apply_screener_filters(df, PRESET_CONFIGS["dividend_champion"])


def apply_debt_free_blue_chip_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Debt-Free Blue Chip preset filters."""
    df_base = apply_screener_filters(df, PRESET_CONFIGS["debt_free_blue_chip_base"])
    if df_base.empty:
        return df_base
    keep_mask = df_base.apply(
        lambda r: is_debt_free(r)
        or (
            r.get("debt_to_equity") <= 0.05
            if pd.notna(r.get("debt_to_equity"))
            else False
        ),
        axis=1,
    )
    return df_base[keep_mask].reset_index(drop=True)


def apply_turnaround_watch_filter(
    df: pd.DataFrame, df_all: pd.DataFrame
) -> pd.DataFrame:
    """Apply the Turnaround Watch preset filters."""
    if df.empty or df_all.empty:
        return pd.DataFrame()

    de_lookup = {}
    for _, row in df_all.iterrows():
        comp_id = str(row["company_id"]).strip()
        try:
            yr = int(float(row["year"]))
            de_lookup[(comp_id, yr)] = row.get("debt_to_equity")
        except (ValueError, TypeError):
            continue

    keep_indices = []
    for idx, row in df.iterrows():
        comp_id = str(row["company_id"]).strip()
        try:
            curr_yr = int(float(row["year"]))
        except (ValueError, TypeError):
            continue

        de_curr = row.get("debt_to_equity")
        de_prev = de_lookup.get((comp_id, curr_yr - 1))

        if pd.notna(de_curr) and de_prev is not None and pd.notna(de_prev):
            if de_curr < de_prev:
                keep_indices.append(idx)

    df_turnaround_candidates = df.loc[keep_indices].copy()
    return apply_screener_filters(
        df_turnaround_candidates, PRESET_CONFIGS["turnaround_watch_base"]
    )


# --- Single Function Call API ---


def screen_quality_compounders(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Quality Compounders in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    return apply_quality_compounder_filter(df_scored)


def screen_value_picks(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Value Picks in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    return apply_value_pick_filter(df_scored)


def screen_growth_accelerators(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Growth Accelerators in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    return apply_growth_accelerator_filter(df_scored)


def screen_dividend_champions(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Dividend Champions in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    return apply_dividend_champion_filter(df_scored)


def screen_debt_free_blue_chips(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Debt-Free Blue Chips in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    return apply_debt_free_blue_chip_filter(df_scored)


def screen_turnaround_watch(
    db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """Screen for Turnaround Watch (declining D/E YoY) in a single function call."""
    df_scored = load_and_score_data(db_path, year=year)
    df_ta_candidates = df_scored[df_scored["de_declined_yoy"]].copy()
    return apply_screener_filters(
        df_ta_candidates, PRESET_CONFIGS["turnaround_watch_base"]
    )


def apply_preset(
    preset_name: str, db_path: Union[str, Path], year: Union[str, int] = 2024
) -> pd.DataFrame:
    """
    Apply a predefined screener preset by name.
    """
    name_clean = str(preset_name).lower().strip().replace(" ", "_").replace("-", "_")

    if name_clean == "quality_compounder":
        return screen_quality_compounders(db_path, year)
    elif name_clean == "value_pick":
        return screen_value_picks(db_path, year)
    elif name_clean == "growth_accelerator":
        return screen_growth_accelerators(db_path, year)
    elif name_clean == "dividend_champion":
        return screen_dividend_champions(db_path, year)
    elif name_clean == "debt_free_blue_chip":
        return screen_debt_free_blue_chips(db_path, year)
    elif name_clean == "turnaround_watch":
        return screen_turnaround_watch(db_path, year)
    else:
        valid_presets = [
            "Quality Compounder",
            "Value Pick",
            "Growth Accelerator",
            "Dividend Champion",
            "Debt-Free Blue Chip",
            "Turnaround Watch",
        ]
        raise ValueError(
            f"Invalid preset name '{preset_name}'. "
            f"Must be one of: {', '.join(valid_presets)}"
        )
