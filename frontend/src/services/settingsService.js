import api from "./api";

export const settingsService = {
  get: () => api.get("/api/settings"),
  update: (valores) => api.put("/api/settings", { valores }),
};
