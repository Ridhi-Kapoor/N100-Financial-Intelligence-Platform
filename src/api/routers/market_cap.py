"""
Market Cap & Valuation History API Router.

Provides endpoints for multi-year historical valuation multiples (P/E, P/B, EV/EBITDA, Dividend Yield).
"""

from fastapi import APIRouter, Depends, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import HistoricalValuationResponse
from src.api.services import get_historical_valuation_service

router = APIRouter(prefix="/market-cap", tags=["Historical Valuation"])


@router.get(
    "/{ticker}",
    response_model=HistoricalValuationResponse,
    summary="Get 2019-2024 historical valuation metrics by ticker",
    status_code=status.HTTP_200_OK,
)
def get_historical_valuation(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> HistoricalValuationResponse:
    """
    Get multi-year historical valuation metrics (P/E, P/B, EV/EBITDA, Dividend Yield) from 2019 to 2024.
    Returns HTTP 404 if ticker is unknown.
    """
    return get_historical_valuation_service(conn, ticker)
