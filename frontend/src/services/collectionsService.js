import api from "./api";

export const collectionsService = {
  registrarPago: (data) => api.post("/api/collections/payments", data),
  cartera: () => api.get("/api/collections/overdue"),
  segmentos: () => api.get("/api/collections/segments"),
};
