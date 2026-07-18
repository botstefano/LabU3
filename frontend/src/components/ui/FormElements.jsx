import { useTheme } from "../../context/ThemeContext";

export function Field({ label, error, children, className = "" }) {
  const { isDark } = useTheme();
  return (
    <div className={`mb-4 ${className}`}>
      {label && <label className={`mb-1.5 block text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-700"}`}>{label}</label>}
      {children}
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

export function Input({ className = "", ...rest }) {
  const { isDark } = useTheme();
  return (
    <input
      className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
        placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600
        ${isDark 
          ? "bg-slate-700 border-slate-600 text-slate-100 placeholder:text-slate-500" 
          : "bg-white border-slate-200 text-slate-900"
        } ${className}`}
      {...rest}
    />
  );
}

export function Select({ className = "", children, ...rest }) {
  const { isDark } = useTheme();
  return (
    <select
      className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
        focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600
        ${isDark 
          ? "bg-slate-700 border-slate-600 text-slate-100" 
          : "bg-white border-slate-200 text-slate-900"
        } ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}
