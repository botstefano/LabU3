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

const ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: null },
  { to: "/clientes", label: "Clientes", icon: Users, roles: null },
  { to: "/facturas", label: "Facturación", icon: FileText, roles: null },
  { to: "/cobranzas", label: "Cobranzas", icon: Landmark, roles: null },
  { to: "/riesgo", label: "Riesgo de Morosidad", icon: BrainCircuit, roles: null },
  { to: "/reportes", label: "Reportes", icon: BarChart3, roles: null },
  { to: "/usuarios", label: "Usuarios", icon: ShieldCheck, roles: ["administrador"] },
  { to: "/configuracion", label: "Configuración", icon: Settings, roles: ["administrador"] },
];

export default function Sidebar() {
  const { user } = useAuth();

  return (
    <aside className="hidden w-64 flex-col border-r border-ink-800 bg-ink-950 px-4 py-6 text-ink-200 md:flex">
      <div className="mb-8 px-2">
        <p className="font-display text-lg font-semibold text-white">Libro Mayor</p>
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
                isActive ? "bg-brand-600 text-white" : "text-ink-300 hover:bg-ink-800 hover:text-white"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-ink-800 px-2 pt-4 text-xs text-ink-500">
        <p>Sistema de Facturación Electrónica</p>
        <p>con Gestión de Cobranzas</p>
      </div>
    </aside>
  );
}
