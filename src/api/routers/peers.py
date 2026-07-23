"""
Peer Group API Router.

Provides endpoints for peer group constituent analysis and percentile rankings.
"""

from fastapi import APIRouter, Depends, status
import sqlite3

from src.api.database import get_db_connection
from src.api.schemas import PeerGroupResponse
from src.api.services import get_peer_group_service

router = APIRouter(prefix="/peers", tags=["Peer Comparison"])


@router.get(
    "/{group_name}",
    response_model=PeerGroupResponse,
    summary="Get companies and KPI percentile ranks for a peer group",
    status_code=status.HTTP_200_OK,
)
def get_peer_group_details(
    group_name: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> PeerGroupResponse:
    """
    Get companies in the requested peer group and their percentile rank for each of 10 selected financial KPIs.
    Returns HTTP 404 if the peer group is unknown.
    """
    return get_peer_group_service(conn, group_name)
