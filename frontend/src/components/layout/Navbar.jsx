import { LogOut, UserCircle, Sun, Moon, Globe } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useTranslation } from "react-i18next";

const ROLE_LABELS = {
  administrador: { es: "Administrador", en: "Administrator" },
  contador: { es: "Contador", en: "Accountant" },
  vendedor: { es: "Vendedor", en: "Seller" },
};

export default function Navbar({ title }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme, language, changeLanguage } = useTheme();
  const { t, i18n } = useTranslation();

  const handleLanguageChange = (lang) => {
    changeLanguage(lang);
    i18n.changeLanguage(lang);
  };

  return (
    <header className={`flex items-center justify-between border-b transition-colors duration-200 ${
      theme === "dark" 
        ? "bg-ink-900 border-ink-800" 
        : "bg-white border-ink-100"
    } px-6 py-4`}>
      <h1 className={`font-display text-xl font-semibold ${
        theme === "dark" ? "text-white" : "text-ink-900"
      }`}>{title}</h1>

      <div className="flex items-center gap-4">
        {/* Language Toggle */}
        <button
          onClick={() => handleLanguageChange(language === "es" ? "en" : "es")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors duration-200 ${
            theme === "dark" 
              ? "text-ink-400 hover:bg-ink-800 hover:text-white" 
              : "text-ink-500 hover:bg-ink-100 hover:text-ink-800"
          }`}
        >
          <Globe size={16} />
          {language.toUpperCase()}
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors duration-200 ${
            theme === "dark" 
              ? "text-ink-400 hover:bg-ink-800 hover:text-white" 
              : "text-ink-500 hover:bg-ink-100 hover:text-ink-800"
          }`}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* User Info */}
        <div className={`flex items-center gap-2 text-sm ${
          theme === "dark" ? "text-ink-400" : "text-ink-600"
        }`}>
          <UserCircle size={20} className="text-ink-400" />
          <div className="leading-tight">
            <p className={`font-medium ${
              theme === "dark" ? "text-white" : "text-ink-800"
            }`}>{user?.nombre}</p>
            <p className="text-xs text-ink-400">
              {ROLE_LABELS[user?.rol]?.[language] || user?.rol}
            </p>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors duration-200 ${
            theme === "dark" 
              ? "text-ink-400 hover:bg-ink-800 hover:text-white" 
              : "text-ink-500 hover:bg-ink-100 hover:text-ink-800"
          }`}
        >
          <LogOut size={16} />
          {t("auth.logout")}
        </button>
      </div>
    </header>
  );
}
