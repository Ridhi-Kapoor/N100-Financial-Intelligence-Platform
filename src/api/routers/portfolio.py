"""
Portfolio & Clustering API Router.

Provides endpoints for K-Means cluster assignments, cluster profiles, and portfolio statistics.
"""

from typing import Any, Dict
from fastapi import APIRouter, status

from src.api.schemas import PortfolioStatsResponse
from src.api.services import get_portfolio_stats_service

router = APIRouter(prefix="/portfolio", tags=["Portfolio & Clustering"])


@router.get(
    "/clusters",
    summary="Get financial cluster assignments",
    status_code=status.HTTP_200_OK,
)
def get_cluster_assignments() -> Dict[str, Any]:
    """
    Get K-Means cluster assignments and descriptive profile labels.
    """
    return {
        "status": "ready",
        "message": "Portfolio & Clustering API endpoint scaffold initialized.",
    }


@router.get(
    "/stats",
    response_model=PortfolioStatsResponse,
    summary="Get portfolio-wide descriptive statistics",
    status_code=status.HTTP_200_OK,
)
def get_portfolio_stats() -> PortfolioStatsResponse:
    """
    Get portfolio-wide percentile statistics (P10, P25, P50, P75, P90, Mean, Std) for the 10 core KPIs.
    """
    return get_portfolio_stats_service()
