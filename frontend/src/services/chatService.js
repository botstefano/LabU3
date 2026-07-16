import api from "./api";

export const chatService = {
  sendMessage: (messages, model = "mistral-large-latest", temperature = 0.7) =>
    api.post("/api/chat/", {
      messages,
      model,
      temperature,
    }),
};
