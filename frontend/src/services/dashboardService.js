import api from "./api";

export const dashboardService = {
  resumen: () => api.get("/api/dashboard"),
};
