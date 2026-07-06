import api from "./api";

export const invoiceService = {
  list: (params) => api.get("/api/invoices", { params }),
  get: (id) => api.get(`/api/invoices/${id}`),
  create: (data) => api.post("/api/invoices", data),
  anular: (id) => api.post(`/api/invoices/${id}/anular`),
  descargarPdf: (id) => api.get(`/api/invoices/${id}/pdf`, { responseType: "blob" }),
};
