import { LogOut, UserCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const ROLE_LABELS = {
  administrador: "Administrador",
  contador: "Contador",
  vendedor: "Vendedor",
};

export default function Navbar({ title }) {
  const { user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b border-ink-100 bg-white px-6 py-4">
      <h1 className="font-display text-xl font-semibold text-ink-900">{title}</h1>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-ink-600">
          <UserCircle size={20} className="text-ink-400" />
          <div className="leading-tight">
            <p className="font-medium text-ink-800">{user?.nombre}</p>
            <p className="text-xs text-ink-400">{ROLE_LABELS[user?.rol] || user?.rol}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-ink-500 hover:bg-ink-100 hover:text-ink-800"
        >
          <LogOut size={16} />
          Salir
        </button>
      </div>
    </header>
  );
}
