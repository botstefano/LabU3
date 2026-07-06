import api from "./api";

export const reportsService = {
  descargarExcel: (params) => api.get("/api/reports/excel", { params, responseType: "blob" }),
  descargarPdf: (params) => api.get("/api/reports/pdf", { params, responseType: "blob" }),
};
