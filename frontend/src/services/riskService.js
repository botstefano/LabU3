
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
  compareModels: () => api.post("/api/risk/compare-models"),
  trainWithType: (modelType) => api.post("/api/risk/train-with-type", { model_type: modelType }),
};

