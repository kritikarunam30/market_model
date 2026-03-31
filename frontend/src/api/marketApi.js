import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

export const fetchRiskIndex = async () => {
  const res = await api.get("/risk-index");
  return res.data;
};

export const fetchVarAnalysis = async () => {
  const res = await api.get("/var-analysis");
  return res.data;
};

export const fetchGrangerAnalysis = async () => {
  const res = await api.get("/granger-analysis");
  return res.data;
};

export const fetchForecast = async () => {
  const res = await api.get("/ml-forecast");
  return res.data;
};

export const fetchNetwork = async () => {
  const res = await api.get("/contagion-network");
  return res.data;
};