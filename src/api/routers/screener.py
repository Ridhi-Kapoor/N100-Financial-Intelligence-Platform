"""
Stock Screener API Router.

Provides endpoints for quantitative stock screening and preset strategy queries.
"""

from typing import Optional
from fastapi import APIRouter, Query, status

from src.api.schemas import ScreenerResponse
from src.api.services import run_screener_service

router = APIRouter(prefix="/screener", tags=["Screener"])


@router.get(
    "",
    response_model=ScreenerResponse,
    summary="Execute quantitative stock screener query",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/",
    response_model=ScreenerResponse,
    summary="Execute quantitative stock screener query",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def run_screener_query(
    min_roe: Optional[float] = Query(
        None, description="Minimum ROE percentage threshold"
    ),
    max_de: Optional[float] = Query(
        None, description="Maximum Debt-to-Equity threshold"
    ),
    min_fcf: Optional[float] = Query(
        None, description="Minimum Free Cash Flow (in Crores)"
    ),
    sector: Optional[str] = Query(None, description="Filter by broad sector name"),
    min_rev_cagr_5yr: Optional[float] = Query(
        None, description="Minimum 5-Year Revenue CAGR percentage"
    ),
    min_pat_cagr_5yr: Optional[float] = Query(
        None, description="Minimum 5-Year PAT CAGR percentage"
    ),
    max_pe: Optional[float] = Query(
        None, description="Maximum Price-to-Earnings ratio threshold"
    ),
) -> ScreenerResponse:
    """
    Execute quantitative stock screening query across financial metrics.

    Returns:
    - Total matching companies
    - Filters applied
    - Sorted results with ranks and latest financial KPIs
    """
    return run_screener_service(
        min_roe=min_roe,
        max_de=max_de,
        min_fcf=min_fcf,
        sector=sector,
        min_rev_cagr_5yr=min_rev_cagr_5yr,
        min_pat_cagr_5yr=min_pat_cagr_5yr,
        max_pe=max_pe,
    )
