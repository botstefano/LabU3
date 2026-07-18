import { useTranslation } from "react-i18next";
import { useTheme } from "../../context/ThemeContext";

const ESTADO_COLORS = {
  PENDIENTE: "bg-amber-100 text-amber-800",
  PAGADA: "bg-emerald-100 text-emerald-800",
  VENCIDA: "bg-red-100 text-red-800",
  ANULADA: "bg-slate-200 text-slate-600",
};

const ESTADO_COLORS_DARK = {
  PENDIENTE: "bg-amber-900/50 text-amber-200 border border-amber-700/50",
  PAGADA: "bg-emerald-900/50 text-emerald-200 border border-emerald-700/50",
  VENCIDA: "bg-red-900/50 text-red-200 border border-red-700/50",
  ANULADA: "bg-slate-700/50 text-slate-300 border border-slate-600/50",
};

export default function EstadoBadge({ estado }) {
  const { t } = useTranslation();
  const { isDark } = useTheme();

  const getTranslatedState = (state) => {
    switch (state?.toUpperCase()) {
      case "PAGADA":
        return t("invoices.paid");
      case "PENDIENTE":
        return t("invoices.pending");
      case "VENCIDA":
        return t("invoices.overdue");
      case "ANULADA":
        return t("invoices.cancelled");
      default:
        return state;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        isDark
          ? ESTADO_COLORS_DARK[estado?.toUpperCase()]
          : ESTADO_COLORS[estado?.toUpperCase()]
      }`}
    >
      {getTranslatedState(estado)}
    </span>
  );
}
