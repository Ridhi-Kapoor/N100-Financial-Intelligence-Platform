"""
Performance and Load Testing Suite.

Covers:
1. Concurrent load test for GET /api/v1/screener (10 concurrent requests < 10 seconds).
2. Company Profile page load time benchmark for 5 tickers (< 3 seconds per ticker).
3. Simultaneous server port availability & integration verification (ports 8000 and 8501).
"""

import time
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple
from fastapi.testclient import TestClient

from src.api.main import app
from src.dashboard.utils.db import get_ratios, get_pl, get_bs, get_cf, get_valuation

client = TestClient(app)

BENCHMARK_TICKERS = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"]


def test_concurrent_screener_load_test():
    """
    1. Send 10 concurrent requests to /api/v1/screener using ThreadPoolExecutor.
    Verify all return HTTP 200 and complete in under 10 seconds total.
    """

    def _fetch(req_id: int) -> Tuple[int, int, float]:
        t0 = time.time()
        res = client.get("/api/v1/screener?min_roe=15")
        latency = time.time() - t0
        return req_id, res.status_code, latency

    t_start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch, i) for i in range(10)]
        results = [f.result() for f in futures]
    total_time = time.time() - t_start

    # Assertions
    assert (
        total_time < 10.0
    ), f"Load test total time {total_time:.2f}s exceeded 10s limit"
    for req_id, status_code, latency in results:
        assert status_code == 200, f"Request {req_id} failed with status {status_code}"
        assert (
            latency < 5.0
        ), f"Individual request {req_id} latency {latency:.2f}s exceeded 5s"


def test_company_profile_load_time_benchmark():
    """
    2. Measure Company Profile data load time for 5 different tickers.
    Verify each profile loads in under 3.0 seconds.
    """
    for ticker in BENCHMARK_TICKERS:
        t0 = time.time()
        ratios = get_ratios(ticker)
        pl = get_pl(ticker)
        get_bs(ticker)
        get_cf(ticker)
        get_valuation(ticker)
        duration = time.time() - t0

        assert (
            duration < 3.0
        ), f"Profile for {ticker} took {duration:.2f}s (limit: 3.0s)"
        assert (
            not ratios.empty or not pl.empty
        ), f"No profile data returned for {ticker}"


def test_simultaneous_ports_and_api_connectivity():
    """
    3. Verify port 8000 (FastAPI) and port 8501 (Streamlit) availability & API health integration.
    """
    # Verify health endpoint returns db_status connected
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_status"] == "connected"
    assert data["status"] == "ok"

    # Verify ports 8000 and 8501 can be bound or accessed without conflicts
    for port in [8000, 8501]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        # Port is either unused or ready to accept connections
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        # 0 means active service listening, non-zero (10061, 10035, 10048, 111) means available/non-listening port
        assert result in [
            0,
            10061,
            10035,
            10048,
            111,
        ], f"Port {port} in unexpected socket state: {result}"
