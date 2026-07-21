import { Loader2, FileSearch, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useTheme } from "../../context/ThemeContext";

export function LoadingState({ message }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  return (
    <div className={`flex flex-col items-center justify-center py-12 ${theme === "dark" ? "text-slate-300" : "text-slate-500"}`}>
      <Loader2 className="h-10 w-10 animate-spin text-blue-600 mb-4" />
      <p className="text-sm">{message || t("common.loading")}</p>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  const { theme } = useTheme();
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-center ${theme === "dark" ? "text-slate-300" : "text-slate-500"}`}>
      {Icon && <Icon className="h-12 w-12 mb-4 opacity-50" />}
      {title && <h3 className={`text-lg font-medium mb-2 ${theme === "dark" ? "text-slate-100" : "text-slate-900"}`}>{title}</h3>}
      {description && <p className="text-sm mb-6 max-w-sm">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retry }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-center ${theme === "dark" ? "text-slate-300" : "text-slate-500"}`}>
      <AlertCircle className="h-12 w-12 mb-4 text-red-500" />
      <h3 className={`text-lg font-medium mb-2 ${theme === "dark" ? "text-slate-100" : "text-slate-900"}`}>{t("common.error")}</h3>
      <p className="text-sm mb-6 max-w-sm">{message || t("common.unexpectedError")}</p>
      {retry && (
        <button
          onClick={retry}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            theme === "dark"
              ? "bg-blue-600 hover:bg-blue-700 text-white"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          }`}
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
