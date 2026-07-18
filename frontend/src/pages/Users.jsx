import { useEffect, useState } from "react";
import { Plus, ShieldCheck } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState } from "../components/ui/States";
import { authService } from "../services/authService";

const USUARIO_VACIO = { nombre: "", email: "", password: "", rol: "vendedor" };

export default function Users() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(USUARIO_VACIO);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const { t } = useTranslation();
  const { theme } = useTheme();

  const cargar = () => {
    setLoading(true);
    authService.listUsers().then((res) => setUsuarios(res.data)).finally(() => setLoading(false));
  };

  useEffect(() => {
    cargar();
  }, []);

  const abrirNuevo = () => {
    setForm(USUARIO_VACIO);
    setError("");
    setModalOpen(true);
  };

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setError("");
    try {
      await authService.createUser(form);
      setModalOpen(false);
      cargar();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : t("common.unexpectedError"));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <AppLayout title={t("users.title")}>
      <Card>
        <div className="mb-4 flex items-center justify-between">
          <p className={`text-sm ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>{t("users.userManagement")}</p>
          <Button onClick={abrirNuevo}>
            <Plus size={16} />
            {t("users.newUser")}
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && (
          <table className="w-full text-sm">
            <thead>
              <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} text-left text-xs uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                <th className="py-2">{t("users.name")}</th>
                <th className="py-2">{t("users.email")}</th>
                <th className="py-2">{t("users.role")}</th>
                <th className="py-2">{t("users.status")}</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id} className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0`}>
                  <td className={`py-2.5 font-medium ${theme === "dark" ? "text-white" : "text-ink-800"}`}>{usuario.nombre}</td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>{usuario.email}</td>
                  <td className="py-2.5">
                    <span className={`inline-flex items-center gap-1 rounded-full ${theme === "dark" ? "bg-ink-800" : "bg-ink-100"} px-2.5 py-1 text-xs font-medium ${theme === "dark" ? "text-ink-300" : "text-ink-700"}`}>
                      <ShieldCheck size={12} />
                      {usuario.rol === "administrador" ? t("users.admin") : usuario.rol === "contador" ? t("users.accountant") : t("users.seller")}
                    </span>
                  </td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>{usuario.activo ? t("users.active") : t("users.inactive")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modalOpen} title={t("users.newUser")} onClose={() => setModalOpen(false)}>
        <form onSubmit={guardar}>
          <Field label={t("users.name")}>
            <Input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
          </Field>
          <Field label={t("users.email")}>
            <Input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>
          <Field label={t("users.tempPassword")}>
            <Input
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>
          <Field label={t("users.role")}>
            <Select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
              <option value="vendedor">{t("users.seller")}</option>
              <option value="contador">{t("users.accountant")}</option>
              <option value="administrador">{t("users.admin")}</option>
            </Select>
          </Field>

          {error && <p className="mb-3 text-sm text-mora-high">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? t("users.creating") : t("users.createUser")}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
