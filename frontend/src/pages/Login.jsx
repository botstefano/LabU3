import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookText, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Field, Input } from "../components/ui/FormElements";
import Button from "../components/ui/Button";
import { useTranslation } from "react-i18next";
import { useTheme } from "../context/ThemeContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`flex min-h-screen items-center justify-center px-4 ${isDark ? "bg-slate-950" : "bg-slate-50"}`}>
      <div className={`w-full max-w-md rounded-2xl p-8 shadow-xl ${isDark ? "bg-slate-800 border border-slate-700" : "bg-white"}`}>
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white">
            <BookText size={24} />
          </div>
          <h1 className={`font-display text-xl font-semibold ${isDark ? "text-slate-100" : "text-slate-900"}`}>Libro Mayor</h1>
          <p className={`text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}>Sistema de Facturación Electrónica y Cobranzas</p>
        </div>

        <form onSubmit={handleSubmit}>
          <Field label={t("auth.email")}>
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="correo@empresa.com"
            />
          </Field>
          <Field label={t("auth.password")}>
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </Field>

          {error && (
            <div className={`mb-4 flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${isDark ? "bg-red-900/30 text-red-300 border border-red-700/50" : "bg-red-50 text-red-700"}`}>
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t("auth.loginLoading") : t("auth.loginBtn")}
          </Button>
        </form>
      </div>
    </div>
  );
}
