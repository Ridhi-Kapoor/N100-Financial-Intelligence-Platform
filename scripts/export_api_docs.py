"""
API Documentation & Postman Collection Exporter Script.

Generates:
1. docs/openapi.json - Complete OpenAPI 3.0 specification from FastAPI app.
2. docs/postman_collection.json - Postman Collection (v2.1.0 format) covering all REST API endpoints.
"""

import json
import logging
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("export_api_docs")

DOCS_DIR = PROJECT_ROOT / "docs"


def export_openapi_json() -> Path:
    """
    Export OpenAPI JSON specification from FastAPI app.
    """
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    openapi_schema = app.openapi()

    output_path = DOCS_DIR / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    logger.info(f"Successfully generated OpenAPI specification: {output_path.resolve()}")
    return output_path


def generate_postman_collection() -> Path:
    """
    Generate Postman Collection v2.1.0 JSON format for all endpoints.
    """
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    baseUrl = "http://127.0.0.1:8000"

    collection = {
        "info": {
            "name": "Nifty 100 Financial Intelligence Platform API",
            "description": "Postman Collection for Nifty 100 REST API exposing financial analytics, stock screening, valuation, peer comparison, sector analytics, portfolio statistics, and company documents.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "nifty100-api-collection-v1",
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": baseUrl,
                "type": "string",
            }
        ],
        "item": [
            {
                "name": "Health Check",
                "item": [
                    {
                        "name": "GET System Health Status",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/health",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "health"],
                            },
                            "description": "Check API status, database connectivity, table row counts, and environment health.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "status": "healthy",
                                        "environment": "development",
                                        "database": {"connected": True, "path": "data/db/nifty100.db", "size_mb": 4.5},
                                        "tables_status": {"companies": 92, "financial_ratios": 552},
                                    },
                                    indent=2,
                                ),
                            }
                        ],
                    }
                ],
            },
            {
                "name": "Stock Screener",
                "item": [
                    {
                        "name": "GET Stock Screener Query",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/screener?min_roe=15&max_de=1.0&min_fcf=100&min_rev_cagr_5yr=10&min_pat_cagr_5yr=10&max_pe=35",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "screener"],
                                "query": [
                                    {"key": "min_roe", "value": "15", "description": "Minimum ROE (%)"},
                                    {"key": "max_de", "value": "1.0", "description": "Maximum Debt-to-Equity"},
                                    {"key": "min_fcf", "value": "100", "description": "Minimum Free Cash Flow (Cr)"},
                                    {"key": "sector", "value": "IT", "disabled": True, "description": "Broad sector filter"},
                                    {"key": "min_rev_cagr_5yr", "value": "10", "description": "Minimum 5Y Revenue CAGR (%)"},
                                    {"key": "min_pat_cagr_5yr", "value": "10", "description": "Minimum 5Y PAT CAGR (%)"},
                                    {"key": "max_pe", "value": "35", "description": "Maximum P/E Ratio"},
                                ],
                            },
                            "description": "Execute quantitative stock screener query across financial metrics.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "total_matches": 2,
                                        "filters_applied": {"min_roe": 15.0, "max_de": 1.0, "max_pe": 35.0},
                                        "results": [
                                            {
                                                "rank": 1,
                                                "company_id": "TCS",
                                                "company_name": "Tata Consultancy Services Ltd",
                                                "sector": "Information Technology",
                                                "latest_kpis": {
                                                    "roe": 48.2,
                                                    "debt_to_equity": 0.08,
                                                    "free_cash_flow": 41500.0,
                                                    "revenue_cagr_5yr": 12.5,
                                                    "pat_cagr_5yr": 11.2,
                                                    "pe_ratio": 29.5,
                                                    "composite_quality_score": 1.05,
                                                },
                                            }
                                        ],
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "400 Bad Request",
                                "status": "Bad Request",
                                "code": 400,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "Invalid parameter value: max_de cannot be negative."}, indent=2),
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Sectors Analytics",
                "item": [
                    {
                        "name": "GET Sector Summaries",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/sectors",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "sectors"],
                            },
                            "description": "Return all broad sectors with company count, median ROE, median P/E, and median Debt-to-Equity.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "total_sectors": 11,
                                        "sectors": [
                                            {
                                                "sector": "Financials",
                                                "company_count": 18,
                                                "median_roe": 14.8,
                                                "median_pe": 18.2,
                                                "median_debt_to_equity": 4.5,
                                            },
                                            {
                                                "sector": "Information Technology",
                                                "company_count": 10,
                                                "median_roe": 28.5,
                                                "median_pe": 28.0,
                                                "median_debt_to_equity": 0.08,
                                            },
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ],
                    },
                    {
                        "name": "GET Sector Companies",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/sectors/Information Technology/companies",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "sectors", "Information Technology", "companies"],
                            },
                            "description": "Return all companies and latest KPIs in the selected broad sector.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "sector": "Information Technology",
                                        "company_count": 10,
                                        "companies": [
                                            {
                                                "company_id": "TCS",
                                                "company_name": "Tata Consultancy Services Ltd",
                                                "sub_sector": "IT Services",
                                                "latest_kpis": {
                                                    "roe": 48.2,
                                                    "roce": 58.5,
                                                    "opm": 26.4,
                                                    "npm": 19.8,
                                                    "debt_to_equity": 0.08,
                                                    "pe_ratio": 29.5,
                                                    "pb_ratio": 13.8,
                                                    "revenue_cagr_5yr": 12.5,
                                                    "pat_cagr_5yr": 11.2,
                                                    "free_cash_flow": 41500.0,
                                                },
                                            }
                                        ],
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "404 Not Found",
                                "status": "Not Found",
                                "code": 404,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "Sector 'NonExistentSector' does not exist."}, indent=2),
                            },
                        ],
                    },
                ],
            },
            {
                "name": "Peer Groups & Comparison",
                "item": [
                    {
                        "name": "GET Peer Group Percentile Ranks",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/peers/IT Services",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "peers", "IT Services"],
                            },
                            "description": "Return companies in a peer group and percentile rank for each of 10 selected KPIs.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "peer_group_name": "IT Services",
                                        "company_count": 5,
                                        "companies": [
                                            {
                                                "company_id": "TCS",
                                                "company_name": "Tata Consultancy Services Ltd",
                                                "is_benchmark": True,
                                                "percentile_ranks": {
                                                    "ROE": 100.0,
                                                    "ROCE": 100.0,
                                                    "Net Profit Margin": 80.0,
                                                    "Debt-to-Equity": 60.0,
                                                    "Free Cash Flow": 100.0,
                                                    "PAT CAGR 5Y": 60.0,
                                                    "Revenue CAGR 5Y": 80.0,
                                                    "EPS CAGR 5Y": 60.0,
                                                    "Interest Coverage Ratio": 100.0,
                                                    "Asset Turnover": 80.0,
                                                },
                                            }
                                        ],
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "404 Not Found",
                                "status": "Not Found",
                                "code": 404,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "Peer group 'Unknown Group' is unknown."}, indent=2),
                            },
                        ],
                    },
                    {
                        "name": "GET Peer Radar Comparison",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/companies/INFY/peers/compare",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "companies", "INFY", "peers", "compare"],
                            },
                            "description": "Return 8-metric radar chart comparison data containing target company values, peer average, and benchmark values.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "ticker": "INFY",
                                        "company_name": "Infosys Ltd",
                                        "peer_group_name": "IT Services",
                                        "benchmark_ticker": "TCS",
                                        "metrics": [
                                            "ROE",
                                            "ROCE",
                                            "Net Profit Margin",
                                            "Debt-to-Equity",
                                            "FCF Score",
                                            "PAT CAGR 5Y",
                                            "Revenue CAGR 5Y",
                                            "Composite Quality Score",
                                        ],
                                        "company_values": {"ROE": 85.0, "ROCE": 88.0, "Net Profit Margin": 75.0},
                                        "peer_group_average": {"ROE": 70.0, "ROCE": 72.0, "Net Profit Margin": 65.0},
                                        "benchmark_values": {"ROE": 98.0, "ROCE": 99.0, "Net Profit Margin": 90.0},
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "404 Not Found",
                                "status": "Not Found",
                                "code": 404,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "Company with ticker 'INVALID' not found."}, indent=2),
                            },
                        ],
                    },
                ],
            },
            {
                "name": "Historical Valuation",
                "item": [
                    {
                        "name": "GET Historical Valuation Multiples",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/market-cap/RELIANCE",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "market-cap", "RELIANCE"],
                            },
                            "description": "Return valuation history from 2019-2024 (P/E, P/B, EV/EBITDA, Dividend Yield).",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "ticker": "RELIANCE",
                                        "company_name": "Reliance Industries Ltd",
                                        "history": [
                                            {
                                                "year": "2019",
                                                "pe_ratio": 21.5,
                                                "pb_ratio": 2.1,
                                                "ev_ebitda": 14.2,
                                                "dividend_yield_pct": 0.55,
                                                "market_cap_crore": 850000.0,
                                            },
                                            {
                                                "year": "2024",
                                                "pe_ratio": 26.8,
                                                "pb_ratio": 2.4,
                                                "ev_ebitda": 16.5,
                                                "dividend_yield_pct": 0.35,
                                                "market_cap_crore": 1950000.0,
                                            },
                                        ],
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "404 Not Found",
                                "status": "Not Found",
                                "code": 404,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "Company with ticker 'UNKNOWN' not found."}, indent=2),
                            },
                        ],
                    }
                ],
            },
            {
                "name": "Portfolio Statistics",
                "item": [
                    {
                        "name": "GET Portfolio Descriptive Statistics",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/portfolio/stats",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "portfolio", "stats"],
                            },
                            "description": "Return P10, P25, P50, P75, P90, Mean, and Standard Deviation for the 10 core KPIs.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "total_kpis": 10,
                                        "statistics": [
                                            {
                                                "kpi_name": "ROE (%)",
                                                "p10": 7.5,
                                                "p25": 11.2,
                                                "p50": 16.8,
                                                "p75": 23.4,
                                                "p90": 34.2,
                                                "mean": 18.5,
                                                "std_dev": 9.2,
                                            }
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ],
                    }
                ],
            },
            {
                "name": "Company Documents",
                "item": [
                    {
                        "name": "GET Company Annual Reports",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/companies/INFY/documents",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "companies", "INFY", "documents"],
                            },
                            "description": "Return Annual Report Title, Report URL, and is_url_valid boolean flag.",
                        },
                        "response": [
                            {
                                "name": "200 OK",
                                "status": "OK",
                                "code": 200,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps(
                                    {
                                        "ticker": "INFY",
                                        "company_name": "Infosys Ltd",
                                        "total_documents": 4,
                                        "documents": [
                                            {
                                                "year": 2024,
                                                "annual_report_title": "Infosys Ltd Annual Report 2024",
                                                "report_url": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/example.pdf",
                                                "is_url_valid": True,
                                            }
                                        ],
                                    },
                                    indent=2,
                                ),
                            },
                            {
                                "name": "404 Not Found",
                                "status": "Not Found",
                                "code": 404,
                                "header": [{"key": "Content-Type", "value": "application/json"}],
                                "body": json.dumps({"detail": "No documents exist for ticker 'UNKNOWN'."}, indent=2),
                            },
                        ],
                    }
                ],
            },
        ],
    }

    output_path = DOCS_DIR / "postman_collection.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)

    logger.info(f"Successfully generated Postman Collection: {output_path.resolve()}")
    return output_path


def main():
    logger.info("Executing API Documentation & Postman Exporter...")
    openapi_file = export_openapi_json()
    postman_file = generate_postman_collection()
    print(f"Docs Generation Complete:\n - OpenAPI Spec: {openapi_file.resolve()}\n - Postman Collection: {postman_file.resolve()}")


if __name__ == "__main__":
    main()
