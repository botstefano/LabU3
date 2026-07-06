export function Field({ label, error, children, className = "" }) {
  return (
    <div className={`mb-4 ${className}`}>
      {label && <label className="mb-1.5 block text-sm font-medium text-ink-700">{label}</label>}
      {children}
      {error && <p className="mt-1 text-xs text-mora-high">{error}</p>}
    </div>
  );
}

export function Input({ className = "", ...rest }) {
  return (
    <input
      className={`w-full rounded-lg border border-ink-200 px-3 py-2 text-sm text-ink-900
        placeholder:text-ink-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 ${className}`}
      {...rest}
    />
  );
}

export function Select({ className = "", children, ...rest }) {
  return (
    <select
      className={`w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900
        focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}
