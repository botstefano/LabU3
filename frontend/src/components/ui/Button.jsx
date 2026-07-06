const VARIANTS = {
  primary: "bg-brand-600 text-white hover:bg-brand-700",
  secondary: "bg-ink-100 text-ink-800 hover:bg-ink-200",
  danger: "bg-mora-high text-white hover:bg-red-700",
  ghost: "bg-transparent text-ink-600 hover:bg-ink-100",
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
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium
        transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
