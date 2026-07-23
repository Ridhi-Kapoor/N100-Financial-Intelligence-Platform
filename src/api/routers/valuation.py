"""
Valuation API Router.

Provides endpoints for valuation multiples, median P/E comparisons, and valuation flags.
"""

from fastapi import APIRouter, Depends, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import HistoricalValuationResponse
from src.api.services import get_historical_valuation_service

router = APIRouter(prefix="/valuation", tags=["Valuation"])


@router.get(
    "/{ticker}",
    response_model=HistoricalValuationResponse,
    summary="Get valuation metrics by ticker",
    status_code=status.HTTP_200_OK,
)
def get_company_valuation(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> HistoricalValuationResponse:
    """
    Get valuation metrics and historical multiples (P/E, P/B, EV/EBITDA, Dividend Yield) by ticker.
    Returns HTTP 404 if ticker is unknown.
    """
    return get_historical_valuation_service(conn, ticker)
