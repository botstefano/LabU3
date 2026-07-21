import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Search, TrendingUp } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState, EmptyState } from "../components/ui/States";
import { clientService } from "../services/clientService";
import { invoiceService } from "../services/invoiceService";

const CLIENTE_VACIO = {
  tipo_documento: "DNI",
  numero_documento: "",
  nombre_razon_social: "",
  direccion: "",
  email: "",
  telefono: "",
};

export default function Clients() {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(CLIENTE_VACIO);
  const [errores, setErrores] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [creditLimit, setCreditLimit] = useState(null);
  const [loadingCredit, setLoadingCredit] = useState(false);
  const { t } = useTranslation();
  const { theme } = useTheme();

  const cargar = async (busqueda = "") => {
    setLoading(true);
    try {
      const res = await clientService.list({ search: busqueda || undefined });
      setClientes(res.data);
    } catch (err) {
      console.error("Error cargando clientes:", err);
      setClientes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const handleSearch = (event) => {
    event.preventDefault();
    cargar(search);
  };

  const handleLoadCreditLimit = async (clientId) => {
    setLoadingCredit(true);
    setCreditLimit(null);
    try {
      const res = await invoiceService.getCreditLimitSuggestion(clientId);
      setCreditLimit(res.data);
    } catch (err) {
      console.error("Error loading credit limit:", err);
    } finally {
      setLoadingCredit(false);
    }
  };

  const abrirNuevo = () => {
    setEditando(null);
    setForm(CLIENTE_VACIO);
    setErrores({});
    setModalOpen(true);
  };

  const abrirEditar = (cliente) => {
    setEditando(cliente);
    setForm({
      tipo_documento: cliente.tipo_documento,
      numero_documento: cliente.numero_documento,
      nombre_razon_social: cliente.nombre_razon_social,
      direccion: cliente.direccion || "",
      email: cliente.email || "",
      telefono: cliente.telefono || "",
    });
    setErrores({});
    setModalOpen(true);
  };

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setErrores({});
    try {
      if (editando) {
        await clientService.update(editando.id, form);
      } else {
        await clientService.create(form);
      }
      setModalOpen(false);
      cargar(search);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setErrores({ general: typeof detail === "string" ? detail : t("common.unexpectedError") });
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (cliente) => {
    if (!window.confirm(t("clients.deleteConfirm", { name: cliente.nombre_razon_social }))) return;
    await clientService.remove(cliente.id);
    cargar(search);
  };

  return (
    <AppLayout title={t("clients.title")}>
      <Card>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <form onSubmit={handleSearch} className="flex w-full max-w-sm items-center gap-2">
            <Input
              placeholder={t("clients.search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button type="submit" variant="secondary">
              <Search size={16} />
            </Button>
          </form>
          <Button onClick={abrirNuevo}>
            <Plus size={16} /> {t("clients.newClient")}
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && clientes.length === 0 && (
          <EmptyState title={t("clients.noClients")} description={t("clients.registerFirstClient")} />
        )}

        {!loading && clientes.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} text-left text-xs uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                <th className="py-2">{t("clients.name")}</th>
                <th className="py-2">{t("clients.docNumber")}</th>
                <th className="py-2">{t("clients.contact")}</th>
                <th className="py-2 text-center">Riesgo (Heurístico)</th>
                <th className="py-2 text-center">Límite Crédito</th>
                <th className="py-2 text-right">{t("clients.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente) => (
                <tr key={cliente.id} className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0`}>
                  <td className={`py-2.5 font-medium ${theme === "dark" ? "text-white" : "text-ink-800"}`}>{cliente.nombre_razon_social}</td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
                    {cliente.tipo_documento} {cliente.numero_documento}
                  </td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>{cliente.email || cliente.telefono || "—"}</td>
                  <td className="py-2.5 text-center">
                    {cliente.riesgo_heuristico && (
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                        cliente.riesgo_heuristico.nivel === 'bajo' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                        cliente.riesgo_heuristico.nivel === 'medio' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                        cliente.riesgo_heuristico.nivel === 'alto' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
                        cliente.riesgo_heuristico.nivel === 'muy_alto' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                      }`}>
                        {cliente.riesgo_heuristico.nivel === 'sin_datos' ? 'Sin datos' :
                         cliente.riesgo_heuristico.nivel === 'bajo' ? 'Bajo' :
                         cliente.riesgo_heuristico.nivel === 'medio' ? 'Medio' :
                         cliente.riesgo_heuristico.nivel === 'alto' ? 'Alto' :
                         cliente.riesgo_heuristico.nivel === 'muy_alto' ? 'Muy Alto' :
                         cliente.riesgo_heuristico.nivel}
                        <span className="text-xs opacity-70">({(cliente.riesgo_heuristico.score * 100).toFixed(0)}%)</span>
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 text-center">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleLoadCreditLimit(cliente.id)}
                      disabled={loadingCredit}
                    >
                      <TrendingUp size={14} />
                    </Button>
                  </td>
                  <td className="py-2.5 text-right">
                    <button onClick={() => abrirEditar(cliente)} className={`mr-2 ${theme === "dark" ? "text-ink-400 hover:text-white" : "text-ink-400 hover:text-brand-600"}`}>
                      <Pencil size={16} />
                    </button>
                    <button onClick={() => eliminar(cliente)} className={`${theme === "dark" ? "text-ink-400 hover:text-red-400" : "text-ink-400 hover:text-mora-high"}`}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {creditLimit && (
        <Modal 
          open={!!creditLimit} 
          title="Sugerencia de Límite de Crédito" 
          onClose={() => setCreditLimit(null)}
        >
          <div className={`rounded-lg p-4 ${theme === "dark" ? "bg-ink-800" : "bg-paper-100"}`}>
            <div className="mb-4">
              <p className={`text-sm ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>Límite sugerido:</p>
              <p className={`text-3xl font-bold ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                S/ {creditLimit.limite_sugerido.toLocaleString("es-PE")}
              </p>
            </div>
            
            <div className={`mb-4 rounded-lg p-3 ${theme === "dark" ? "bg-ink-700" : "bg-white"}`}>
              <p className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                Nivel de riesgo (heurístico): {creditLimit.nivel_riesgo.toUpperCase()}
              </p>
              <p className={`text-sm ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                Score de riesgo: {(creditLimit.score_riesgo * 100).toFixed(0)}%
              </p>
            </div>

            <div className={`mb-4 rounded-lg p-3 ${theme === "dark" ? "bg-ink-700" : "bg-white"}`}>
              <p className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                Justificación:
              </p>
              <p className={`text-sm ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                {creditLimit.justificacion}
              </p>
            </div>

            <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-ink-700" : "bg-white"}`}>
              <p className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                Factores considerados:
              </p>
              <ul className={`text-sm space-y-1 ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                <li>% Facturas vencidas: {(creditLimit.factores.pct_facturas_vencidas * 100).toFixed(1)}%</li>
                <li>% Pagos tardíos: {(creditLimit.factores.pct_pagos_tardios * 100).toFixed(1)}%</li>
                <li>Días mora promedio: {creditLimit.factores.dias_mora_promedio.toFixed(1)} días</li>
              </ul>
            </div>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCreditLimit(null)}>
              Cerrar
            </Button>
          </div>
        </Modal>
      )}

      <Modal open={modalOpen} title={editando ? t("clients.editClient") : t("clients.newClient")} onClose={() => setModalOpen(false)}>
        <form onSubmit={guardar}>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("clients.docType")}>
              <Select
                value={form.tipo_documento}
                onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })}
              >
                <option value="DNI">{t("clients.dni")}</option>
                <option value="RUC">{t("clients.ruc")}</option>
              </Select>
            </Field>
            <Field label={t("clients.docNumber")}>
              <Input
                required
                value={form.numero_documento}
                onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
              />
            </Field>
          </div>
          <Field label={t("clients.name")}>
            <Input
              required
              value={form.nombre_razon_social}
              onChange={(e) => setForm({ ...form, nombre_razon_social: e.target.value })}
            />
          </Field>
          <Field label={t("clients.address")}>
            <Input value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("auth.email")}>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label={t("clients.contact")}>
              <Input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
            </Field>
          </div>

          {errores.general && <p className="mb-3 text-sm text-mora-high">{errores.general}</p>}

          <div className="mt-2 flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? t("clients.saving") : t("clients.save")}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
