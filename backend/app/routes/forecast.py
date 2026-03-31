from fastapi import APIRouter
from app.services.data_service import fetch_market_data
from app.services.forecast_service import run_xgboost_forecast

router = APIRouter()

@router.get("/ml-forecast")
def get_ml_forecast():
    prices = fetch_market_data()
    return run_xgboost_forecast(prices)