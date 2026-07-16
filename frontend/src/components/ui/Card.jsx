import { useTheme } from "../../context/ThemeContext";

export default function Card({ children, className = "", title, action }) {
  const { theme } = useTheme();
  
  return (
    <div className={`rounded-xl border transition-colors duration-200 p-5 shadow-card ${
      theme === "dark" 
        ? "border-ink-800 bg-ink-900" 
        : "border-ink-100 bg-white"
    } ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className={`font-display text-sm font-semibold uppercase tracking-wide ${
            theme === "dark" ? "text-ink-300" : "text-ink-600"
          }`}>{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
