import { useTheme } from "../../context/ThemeContext";

const VARIANTS = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "bg-transparent text-slate-600 hover:bg-slate-100",
};

const VARIANTS_DARK = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "bg-slate-700 text-slate-200 hover:bg-slate-600 border border-slate-600",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "bg-transparent text-slate-300 hover:bg-slate-700/50",
};

export default function Button({
  children,
  variant = "primary",
  className = "",
  type = "button",
  disabled = false,
  onClick,
  ...rest
}) {
  const { isDark } = useTheme();

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium
        transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
          isDark ? VARIANTS_DARK[variant] : VARIANTS[variant]
        } ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
