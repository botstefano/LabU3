export default function Card({ children, className = "", title, action }) {
  return (
    <div className={`rounded-xl border border-ink-100 bg-white p-5 shadow-card ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-ink-600">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
