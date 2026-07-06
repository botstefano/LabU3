import api from "./api";

export const authService = {
  login: (email, password) => api.post("/api/auth/login", { email, password }),
  me: () => api.get("/api/auth/me"),
  listUsers: () => api.get("/api/auth/users"),
  createUser: (data) => api.post("/api/auth/users", data),
};
