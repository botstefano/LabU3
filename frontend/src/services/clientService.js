import api from "./api";

export const clientService = {
  list: (params) => api.get("/api/clients", { params }),
  get: (id) => api.get(`/api/clients/${id}`),
  create: (data) => api.post("/api/clients", data),
  update: (id, data) => api.put(`/api/clients/${id}`, data),
  remove: (id) => api.delete(`/api/clients/${id}`),
};
