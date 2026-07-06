import { Loader2, Inbox, AlertTriangle } from "lucide-react";

export function LoadingState({ label = "Cargando..." }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-ink-400">
      <Loader2 className="animate-spin" size={20} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({ title = "Sin resultados", description }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-ink-400">
      <Inbox size={28} />
      <p className="text-sm font-medium text-ink-600">{title}</p>
      {description && <p className="max-w-sm text-xs text-ink-400">{description}</p>}
    </div>
  );
}

export function ErrorState({ message = "Ocurrio un error inesperado" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg bg-red-50 py-10 text-center text-mora-high">
      <AlertTriangle size={22} />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
