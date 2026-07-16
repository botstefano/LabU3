import { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff, X, MessageSquare, Bot, User } from "lucide-react";
import { chatService } from "../services/chatService";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";

export default function Chatbot() {
  const { theme } = useTheme();
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: t("chatbot.placeholder") || "¡Hola! ¿En qué puedo ayudarte hoy?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  useEffect(() => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = "es-ES";

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        handleSend(transcript);
      };

      recognitionRef.current.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleSend = async (text = input) => {
    if (!text.trim() || isLoading) return;

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await chatService.sendMessage([
        {
          role: "system",
          content:
            "You are a helpful assistant for an electronic invoicing system. Answer questions in the user's language. Be friendly and concise.",
        },
        ...messages,
        userMessage,
      ]);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.data.content },
      ]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Lo siento, no puedo responder en este momento.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {isOpen && (
        <div
          className={`mb-4 w-96 rounded-2xl shadow-xl transition-all duration-300 ${
            theme === "dark"
              ? "bg-ink-900 border border-ink-800"
              : "bg-white border border-ink-200"
          }`}
        >
          {/* Header */}
          <div
            className={`flex items-center justify-between p-4 rounded-t-2xl border-b ${
              theme === "dark"
                ? "bg-brand-600 border-brand-700"
                : "bg-brand-600 border-brand-700"
            }`}
          >
            <div className="flex items-center gap-2 text-white">
              <Bot size={20} />
              <h3 className="font-semibold">{t("chatbot.title")}</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white hover:bg-white/20 p-1 rounded-lg"
            >
              <X size={20} />
            </button>
          </div>

          {/* Messages */}
          <div className="h-96 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      theme === "dark" ? "bg-brand-700" : "bg-brand-600"
                    }`}
                  >
                    <Bot size={16} className="text-white" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? theme === "dark"
                        ? "bg-brand-600 text-white"
                        : "bg-brand-600 text-white"
                      : theme === "dark"
                      ? "bg-ink-800 text-ink-200"
                      : "bg-ink-100 text-ink-800"
                  }`}
                >
                  {msg.content}
                </div>
                {msg.role === "user" && (
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      theme === "dark" ? "bg-ink-700" : "bg-ink-200"
                    }`}
                  >
                    <User size={16} className={theme === "dark" ? "text-white" : "text-ink-700"} />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    theme === "dark" ? "bg-brand-700" : "bg-brand-600"
                  }`}
                >
                  <Bot size={16} className="text-white" />
                </div>
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    theme === "dark" ? "bg-ink-800 text-ink-200" : "bg-ink-100 text-ink-800"
                  }`}
                >
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-ink-200 dark:border-ink-800">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={t("chatbot.placeholder")}
                className={`flex-1 px-4 py-2 rounded-full border focus:outline-none focus:ring-2 focus:ring-brand-500 ${
                  theme === "dark"
                    ? "bg-ink-800 border-ink-700 text-white placeholder-ink-400"
                    : "bg-ink-50 border-ink-200 text-ink-800 placeholder-ink-500"
                }`}
              />
              <button
                onClick={toggleListening}
                disabled={!recognitionRef.current}
                className={`p-2 rounded-full ${
                  isListening
                    ? "bg-red-500 text-white animate-pulse"
                    : theme === "dark"
                    ? "bg-ink-800 text-ink-200 hover:bg-ink-700"
                    : "bg-ink-100 text-ink-700 hover:bg-ink-200"
                }`}
              >
                {isListening ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isLoading}
                className="p-2 rounded-full bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send size={20} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-transform duration-300 hover:scale-110 ${
          theme === "dark" 
            ? "bg-brand-600 text-white" 
            : "bg-brand-600 text-white"
        }`}
      >
        <MessageSquare size={28} />
      </button>
    </div>
  );
}
