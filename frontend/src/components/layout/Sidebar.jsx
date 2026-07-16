import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  FileText,
  Landmark,
  BarChart3,
  Settings,
  ShieldCheck,
  BrainCircuit,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useTranslation } from "react-i18next";

export default function Sidebar() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const { t } = useTranslation();

  const ITEMS = [
    { to: "/", label: t("nav.dashboard"), icon: LayoutDashboard, roles: null },
    { to: "/clientes", label: t("nav.clients"), icon: Users, roles: null },
    { to: "/facturas", label: t("nav.invoices"), icon: FileText, roles: null },
    { to: "/cobranzas", label: t("nav.collections"), icon: Landmark, roles: null },
    { to: "/riesgo", label: t("nav.risk"), icon: BrainCircuit, roles: null },
    { to: "/reportes", label: t("nav.reports"), icon: BarChart3, roles: null },
    { to: "/usuarios", label: t("nav.users"), icon: ShieldCheck, roles: ["administrador"] },
    { to: "/configuracion", label: t("nav.settings"), icon: Settings, roles: ["administrador"] },
  ];

  return (
    <aside className={`hidden w-64 flex-col border-r transition-colors duration-200 ${
      theme === "dark" 
        ? "border-ink-800 bg-ink-950 text-ink-200" 
        : "border-ink-100 bg-white text-ink-700"
    } px-4 py-6 md:flex`}>
      <div className="mb-8 px-2">
        <p className={`font-display text-lg font-semibold ${
          theme === "dark" ? "text-white" : "text-ink-900"
        }`}>Libro Mayor</p>
        <p className="text-xs text-ink-400">Facturación electrónica</p>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {ITEMS.filter((item) => !item.roles || item.roles.includes(user?.rol?.toLowerCase())).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive 
                  ? "bg-brand-600 text-white" 
                  : theme === "dark" 
                    ? "text-ink-300 hover:bg-ink-800 hover:text-white" 
                    : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className={`mt-auto border-t px-2 pt-4 text-xs text-ink-500 ${
        theme === "dark" ? "border-ink-800" : "border-ink-100"
      }`}>
        <p>Sistema de Facturación Electrónica</p>
        <p>con Gestión de Cobranzas</p>
      </div>
    </aside>
  );
}
