const ESTILOS = {
  pendiente: "bg-amber-100 text-amber-800",
  pagada: "bg-brand-100 text-brand-700",
  vencida: "bg-red-100 text-red-700",
  anulada: "bg-ink-100 text-ink-500",
};

const ETIQUETAS = {
  pendiente: "Pendiente",
  pagada: "Pagada",
  vencida: "Vencida",
  anulada: "Anulada",
};

export default function EstadoBadge({ estado }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${ESTILOS[estado] || "bg-ink-100 text-ink-600"}`}>
      {ETIQUETAS[estado] || estado}
    </span>
  );
}
