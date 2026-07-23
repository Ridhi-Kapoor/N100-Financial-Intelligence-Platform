"""
Pydantic Schemas for Day 40 API Endpoints.

Defines response models and validation schemas for:
- Stock Screener
- Sector Analytics & Company Listings
- Peer Groups & Peer Comparison (Radar)
- Historical Valuation
- Portfolio Statistics
- Company Documents
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Stock Screener Schemas
# ---------------------------------------------------------------------------
class ScreenerKPIs(BaseModel):
    roe: Optional[float] = Field(None, description="Return on Equity (%)")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-Equity Ratio")
    free_cash_flow: Optional[float] = Field(
        None, description="Free Cash Flow in Crores"
    )
    revenue_cagr_5yr: Optional[float] = Field(
        None, description="5-Year Revenue CAGR (%)"
    )
    pat_cagr_5yr: Optional[float] = Field(None, description="5-Year PAT CAGR (%)")
    pe_ratio: Optional[float] = Field(None, description="Price to Earnings Ratio")
    composite_quality_score: Optional[float] = Field(
        None, description="Composite Quality Score"
    )


class ScreenerResultItem(BaseModel):
    rank: int = Field(..., description="Screening Rank (1-indexed)")
    company_id: str = Field(..., description="NSE Ticker Symbol")
    company_name: str = Field(..., description="Company Name")
    sector: str = Field(..., description="Broad Sector")
    latest_kpis: ScreenerKPIs = Field(
        ..., description="Latest financial KPIs used for screening"
    )


class ScreenerResponse(BaseModel):
    total_matches: int = Field(
        ..., description="Total companies matching screening criteria"
    )
    filters_applied: Dict[str, Any] = Field(..., description="Filters applied in query")
    results: List[ScreenerResultItem] = Field(
        ..., description="Filtered companies sorted by quality score"
    )


# ---------------------------------------------------------------------------
# 2. Sector Analytics Schemas
# ---------------------------------------------------------------------------
class SectorSummaryItem(BaseModel):
    sector: str = Field(..., description="Broad Sector Name")
    company_count: int = Field(..., description="Number of constituent companies")
    median_roe: Optional[float] = Field(None, description="Median ROE (%)")
    median_pe: Optional[float] = Field(None, description="Median P/E Ratio")
    median_debt_to_equity: Optional[float] = Field(
        None, description="Median Debt-to-Equity Ratio"
    )


class SectorSummaryResponse(BaseModel):
    total_sectors: int = Field(..., description="Total broad sectors")
    sectors: List[SectorSummaryItem] = Field(..., description="Sector summaries")


class CompanyKPIs(BaseModel):
    roe: Optional[float] = None
    roce: Optional[float] = None
    opm: Optional[float] = None
    npm: Optional[float] = None
    debt_to_equity: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    revenue_cagr_5yr: Optional[float] = None
    pat_cagr_5yr: Optional[float] = None
    free_cash_flow: Optional[float] = None


class SectorCompanyItem(BaseModel):
    company_id: str = Field(..., description="NSE Ticker Symbol")
    company_name: str = Field(..., description="Company Name")
    sub_sector: Optional[str] = Field(None, description="Sub-Sector Name")
    latest_kpis: CompanyKPIs = Field(..., description="Latest financial KPIs")


class SectorCompaniesResponse(BaseModel):
    sector: str = Field(..., description="Selected Broad Sector Name")
    company_count: int = Field(..., description="Number of companies in sector")
    companies: List[SectorCompanyItem] = Field(..., description="Companies in sector")


# ---------------------------------------------------------------------------
# 3. Peer Groups & Peer Comparison Schemas
# ---------------------------------------------------------------------------
class PeerCompanyItem(BaseModel):
    company_id: str = Field(..., description="NSE Ticker Symbol")
    company_name: str = Field(..., description="Company Name")
    is_benchmark: bool = Field(
        False, description="Flag indicating if company is benchmark for group"
    )
    percentile_ranks: Dict[str, Optional[float]] = Field(
        ..., description="Percentile ranks across 10 KPIs"
    )


class PeerGroupResponse(BaseModel):
    peer_group_name: str = Field(..., description="Peer Group Name")
    company_count: int = Field(..., description="Number of companies in peer group")
    companies: List[PeerCompanyItem] = Field(..., description="Companies in peer group")


class PeerComparisonResponse(BaseModel):
    ticker: str = Field(..., description="Target Company Ticker")
    company_name: str = Field(..., description="Target Company Name")
    peer_group_name: str = Field(..., description="Peer Group Name")
    benchmark_ticker: Optional[str] = Field(
        None, description="Benchmark Company Ticker"
    )
    metrics: List[str] = Field(
        ..., description="8 Financial Metrics used for Radar Chart"
    )
    company_values: Dict[str, Optional[float]] = Field(
        ..., description="Target company values/scores for 8 metrics"
    )
    peer_group_average: Dict[str, Optional[float]] = Field(
        ..., description="Peer group average values/scores"
    )
    benchmark_values: Dict[str, Optional[float]] = Field(
        ..., description="Benchmark company values/scores"
    )


# ---------------------------------------------------------------------------
# 4. Historical Valuation Schemas
# ---------------------------------------------------------------------------
class HistoricalValuationItem(BaseModel):
    year: str = Field(..., description="Financial Year (e.g. 2024)")
    pe_ratio: Optional[float] = Field(None, description="Price to Earnings Ratio")
    pb_ratio: Optional[float] = Field(None, description="Price to Book Ratio")
    ev_ebitda: Optional[float] = Field(None, description="EV / EBITDA Ratio")
    dividend_yield_pct: Optional[float] = Field(None, description="Dividend Yield (%)")
    market_cap_crore: Optional[float] = Field(
        None, description="Market Capitalization in Crores"
    )
    enterprise_value_crore: Optional[float] = Field(
        None, description="Enterprise Value in Crores"
    )


class HistoricalValuationResponse(BaseModel):
    ticker: str = Field(..., description="NSE Ticker Symbol")
    company_name: str = Field(..., description="Company Name")
    history: List[HistoricalValuationItem] = Field(
        ..., description="Valuation history 2019-2024"
    )


# ---------------------------------------------------------------------------
# 5. Portfolio Statistics Schemas
# ---------------------------------------------------------------------------
class PortfolioKPIStats(BaseModel):
    kpi_name: str = Field(..., description="KPI Display Name")
    p10: float = Field(..., description="10th Percentile")
    p25: float = Field(..., description="25th Percentile")
    p50: float = Field(..., description="50th Percentile (Median)")
    p75: float = Field(..., description="75th Percentile")
    p90: float = Field(..., description="90th Percentile")
    mean: float = Field(..., description="Mean Value")
    std_dev: float = Field(..., description="Standard Deviation")


class PortfolioStatsResponse(BaseModel):
    total_kpis: int = Field(..., description="Number of core KPIs evaluated")
    statistics: List[PortfolioKPIStats] = Field(
        ..., description="Descriptive statistics for core KPIs"
    )


# ---------------------------------------------------------------------------
# 6. Company Documents Schemas
# ---------------------------------------------------------------------------
class DocumentItem(BaseModel):
    year: Optional[int] = Field(None, description="Report Year")
    annual_report_title: str = Field(..., description="Annual Report Title")
    report_url: str = Field(..., description="BSE/Company Report Download URL")
    is_url_valid: bool = Field(
        ..., description="Flag indicating if URL is available/valid"
    )


class CompanyDocumentsResponse(BaseModel):
    ticker: str = Field(..., description="NSE Ticker Symbol")
    company_name: str = Field(..., description="Company Name")
    total_documents: int = Field(..., description="Total documents available")
    documents: List[DocumentItem] = Field(
        ..., description="List of company annual report documents"
    )
