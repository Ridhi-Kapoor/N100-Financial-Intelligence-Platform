"""
Documents & PDF Reports API Router.

Provides endpoints for downloading generated company tearsheet PDFs, portfolio summaries, and annual report documents.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import CompanyDocumentsResponse
from src.api.services import get_company_documents_service

router = APIRouter(prefix="/documents", tags=["Documents & Reports"])


@router.get(
    "/tearsheet/{ticker}",
    summary="Download company tearsheet PDF",
    status_code=status.HTTP_200_OK,
)
def get_tearsheet_pdf(ticker: str) -> Dict[str, Any]:
    """
    Download 2-page company tearsheet PDF by ticker.
    """
    clean_ticker = ticker.strip().upper()
    return {
        "ticker": clean_ticker,
        "status": "ready",
        "message": f"Document download endpoint scaffold initialized for {clean_ticker}_tearsheet.pdf.",
    }


@router.get(
    "/{ticker}",
    response_model=CompanyDocumentsResponse,
    summary="Get annual report documents by ticker",
    status_code=status.HTTP_200_OK,
)
def get_documents_by_ticker(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> CompanyDocumentsResponse:
    """
    Get annual report documents, report URLs, and URL validity flags for a company.
    Returns HTTP 404 if no documents exist for the ticker.
    """
    return get_company_documents_service(conn, ticker)
