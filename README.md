# Global Market Contagion Platform

A lightweight web application for analyzing systemic risk and market contagion using econometric models and machine learning.

## Features

- **Market Risk Index**: Real-time composite risk scoring with historical tracking
- **VAR Spillover Analysis**: Cross-market risk transmission analysis using Vector Autoregression
- **Granger Causality Analysis**: Identify probable sources of market contagion
- **ML Risk Forecasting**: XGBoost-powered predictions for next-day risk levels
- **Contagion Network**: Interactive graph visualization of systemic risk propagation

## Tech Stack

### Backend
- FastAPI
- Python 3.9+
- statsmodels (VAR, Granger causality)
- XGBoost
- NetworkX

### Frontend
- React 18
- Vite
- TailwindCSS
- Axios

## Installation

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Market Download Tuning (Rate Limit Handling)

The market downloader now supports environment variables for retry and pacing control.
These settings are used by:

- `backend/download_data.py`
- `backend/app/services/data_service.py` when `data/market_data.csv` is missing

Available variables:

- `MARKET_DL_BATCH_SIZE` (default: `4`)
- `MARKET_DL_MAX_RETRIES` (default: `4`)
- `MARKET_DL_BASE_SLEEP_SECONDS` (default: `2.0`)
- `MARKET_DL_JITTER_SECONDS` (default: `0.75`)

Example (Git Bash):

```bash
cd backend
MARKET_DL_BATCH_SIZE=2 \
MARKET_DL_MAX_RETRIES=5 \
MARKET_DL_BASE_SLEEP_SECONDS=1.5 \
MARKET_DL_JITTER_SECONDS=0.8 \
python download_data.py
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend Server

```bash
cd backend
uvicorn app.main:app
or 
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`

## API Endpoints

- `GET /api/risk-index` - Get current risk index and historical data
- `GET /api/var-analysis` - Perform VAR analysis for contagion timing
- `GET /api/granger-analysis` - Identify probable contagion sources
- `GET /api/ml-forecast` - Predict next-day risk levels
- `GET /api/contagion-network` - Retrieve contagion network data

## Project Structure

```
market_model/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── schemas/
│   │   └── models/
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   ├── components/
    │   ├── api/
    │   └── charts/
    ├── package.json
    └── vite.config.js
```

## Key Models

1. **VAR (Vector Autoregression)**: Captures dynamic interdependencies between markets
2. **GARCH**: Models time-varying volatility and volatility clustering
3. **XGBoost**: Machine learning forecasting with feature importance
4. **Network Analysis**: Graph-based systemic importance metrics

## Development

### Add New Market

Edit `backend/app/services/risk_service.py` and update the `markets` list.

### Customize Styling

Edit `frontend/tailwind.config.js` for theme colors and `frontend/src/index.css` for custom styles.

## License

MIT

## Authors

Kriti Karunam
