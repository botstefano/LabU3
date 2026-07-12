
import api from "./api";

export const riskService = {
  train: () => api.post("/api/risk/train"),
  listClients: () => api.get("/api/risk/clients"),
  getClient: (clientId) => api.get(`/api/risk/clients/${clientId}`),
};

