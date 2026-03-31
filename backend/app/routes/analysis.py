from fastapi import APIRouter
from app.services.data_service import fetch_market_data
from app.services.analysis_service import run_var_analysis, run_granger_analysis

router = APIRouter()

@router.get("/var-analysis")
def get_var_analysis():
    prices = fetch_market_data()
    return run_var_analysis(prices)

@router.get("/granger-analysis")
def get_granger_analysis():
    prices = fetch_market_data()
    return run_granger_analysis(prices)