
import api from "./api";

export const riskService = {
  train: () => api.post("/api/risk/train"),
  uploadDataset: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post("/api/risk/upload-dataset", formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  getTrainingStatus: () => api.get("/api/risk/training-status"),
  listClients: () => api.get("/api/risk/clients"),
  getClient: (clientId) => api.get(`/api/risk/clients/${clientId}`),
};

