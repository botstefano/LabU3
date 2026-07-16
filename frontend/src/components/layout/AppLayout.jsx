import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Chatbot from "../Chatbot";
import { useTheme } from "../../context/ThemeContext";

export default function AppLayout({ title, children }) {
  const { theme } = useTheme();
  
  return (
    <div className={`flex min-h-screen transition-colors duration-200 ${
      theme === "dark" ? "bg-ink-950" : "bg-paper-50"
    }`}>
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Navbar title={title} />
        <main className={`flex-1 overflow-y-auto p-6 transition-colors duration-200 ${
          theme === "dark" ? "text-ink-200" : "text-ink-900"
        }`}>
          {children}
        </main>
      </div>
      <Chatbot />
    </div>
  );
}
