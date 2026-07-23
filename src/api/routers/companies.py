"""
Companies API Router.

Provides endpoints for company listings, profile details, peer comparison radar data, and company documents.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import PeerComparisonResponse, CompanyDocumentsResponse
from src.api.services import (
    get_peer_comparison_radar_service,
    get_company_documents_service,
)

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get(
    "",
    summary="List all companies",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/",
    summary="List all companies",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_companies(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    List all Nifty 100 constituents.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, company_name, roce_percentage, roe_percentage FROM companies WHERE company_name NOT LIKE '%(Stub)' ORDER BY id ASC"
    )
    rows = [dict(row) for row in cursor.fetchall()]
    return {"total": len(rows), "companies": rows}


@router.get(
    "/{ticker}/peers/compare",
    response_model=PeerComparisonResponse,
    summary="Get 8-metric peer radar chart comparison data",
    status_code=status.HTTP_200_OK,
)
def get_company_peer_comparison(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> PeerComparisonResponse:
    """
    Get 8-metric radar chart comparison data containing target company values, peer group average,
    and benchmark company values.
    Returns HTTP 404 if ticker is unknown.
    """
    return get_peer_comparison_radar_service(conn, ticker)


@router.get(
    "/{ticker}/documents",
    response_model=CompanyDocumentsResponse,
    summary="Get annual report documents and link validity for a company",
    status_code=status.HTTP_200_OK,
)
def get_company_documents(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> CompanyDocumentsResponse:
    """
    Get list of annual report documents, BSE report URLs, and URL validity flags for a company.
    Returns HTTP 404 if no documents exist for the ticker.
    """
    return get_company_documents_service(conn, ticker)


@router.get(
    "/{ticker}",
    summary="Get company profile by ticker",
    status_code=status.HTTP_200_OK,
)
def get_company_profile(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    Get detailed company profile and fundamental indicators by NSE ticker symbol.
    """
    clean_ticker = ticker.strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM companies WHERE id = ?", (clean_ticker,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{clean_ticker}' not found.",
        )
    return dict(row)
