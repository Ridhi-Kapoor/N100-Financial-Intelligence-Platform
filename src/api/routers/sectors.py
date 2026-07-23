"""
Sectors API Router.

Provides endpoints for sector summary aggregations, median KPIs, and sector constituents.
"""

from fastapi import APIRouter, Depends, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import SectorSummaryResponse, SectorCompaniesResponse
from src.api.services import get_sectors_summary_service, get_sector_companies_service

router = APIRouter(prefix="/sectors", tags=["Sectors"])


@router.get(
    "",
    response_model=SectorSummaryResponse,
    summary="List all broad sectors with median KPIs",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/",
    response_model=SectorSummaryResponse,
    summary="List all broad sectors with median KPIs",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_sectors(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> SectorSummaryResponse:
    """
    Get sector summary analytics including company count, median ROE, median P/E, and median Debt-to-Equity.
    """
    return get_sectors_summary_service(conn)


@router.get(
    "/{sector}/companies",
    response_model=SectorCompaniesResponse,
    summary="Get all companies and latest KPIs in a sector",
    status_code=status.HTTP_200_OK,
)
def get_sector_companies(
    sector: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> SectorCompaniesResponse:
    """
    Get all companies belonging to the selected broad sector with their latest financial KPIs.
    Returns HTTP 404 if sector does not exist.
    """
    return get_sector_companies_service(conn, sector)
