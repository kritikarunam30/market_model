from fastapi import APIRouter
from app.services.data_service import fetch_market_data
from app.services.network_service import build_network

router = APIRouter()

@router.get("/contagion-network")
def get_contagion_network():
    prices = fetch_market_data()
    return build_network(prices)