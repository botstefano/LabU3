import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, Filter } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import EstadoBadge from "../components/ui/EstadoBadge";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState, EmptyState } from "../components/ui/States";
import { invoiceService } from "../services/invoiceService";
import { clientService } from "../services/clientService";

function formatMonto(valor) {
  return `S/ ${Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

const ITEM_VACIO = { descripcion: "", cantidad: 1, precio_unitario: 0 };

export default function Invoices() {
  const navigate = useNavigate();
  const [facturas, setFacturas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ estado: "", fecha_desde: "", fecha_hasta: "" });

  const [modalOpen, setModalOpen] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [form, setForm] = useState({ client_id: "", fecha_vencimiento: "", items: [{ ...ITEM_VACIO }] });
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [riskAlert, setRiskAlert] = useState(null);
  const { t } = useTranslation();
  const { theme } = useTheme();

  const cargarFacturas = async (params = {}) => {
    setLoading(true);
    try {
      const query = {};
      if (params.estado || filtros.estado) query.estado = params.estado ?? filtros.estado;
      if (params.fecha_desde || filtros.fecha_desde) query.fecha_desde = params.fecha_desde ?? filtros.fecha_desde;
      if (params.fecha_hasta || filtros.fecha_hasta) query.fecha_hasta = params.fecha_hasta ?? filtros.fecha_hasta;
      const res = await invoiceService.list(query);
      setFacturas(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarFacturas();
    clientService.list({ limit: 200 }).then((res) => setClientes(res.data));
  }, []);

  const aplicarFiltros = (event) => {
    event.preventDefault();
    cargarFacturas();
  };

  const abrirNueva = () => {
    setForm({ client_id: "", fecha_vencimiento: "", items: [{ ...ITEM_VACIO }] });
    setError("");
    setModalOpen(true);
  };

  const actualizarItem = (index, campo, valor) => {
    const items = [...form.items];
    items[index] = { ...items[index], [campo]: valor };
    setForm({ ...form, items });
  };

  const agregarItem = () => setForm({ ...form, items: [...form.items, { ...ITEM_VACIO }] });
  const quitarItem = (index) => setForm({ ...form, items: form.items.filter((_, i) => i !== index) });

  const subtotalEstimado = form.items.reduce(
    (acc, item) => acc + Number(item.cantidad || 0) * Number(item.precio_unitario || 0),
    0
  );
  const igvEstimado = subtotalEstimado * 0.18;

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setError("");
    setRiskAlert(null);
    try {
      const payload = {
        ...form,
        items: form.items.map((item) => ({
          descripcion: item.descripcion,
          cantidad: Number(item.cantidad),
          precio_unitario: Number(item.precio_unitario),
        })),
      };
      const res = await invoiceService.create(payload);
      
      // Mostrar alerta de riesgo si existe
      if (res.data.risk_alert) {
        setRiskAlert(res.data.risk_alert);
        setGuardando(false);
        return; // No cerrar modal para que el usuario vea la alerta
      }
      
      setModalOpen(false);
      cargarFacturas();
      navigate(`/facturas/${res.data.invoice.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : t("common.unexpectedError"));
      setGuardando(false);
    }
  };

  const confirmarConRiesgo = () => {
    setRiskAlert(null);
    setModalOpen(false);
    cargarFacturas();
  };

  return (
    <AppLayout title={t("invoices.title")}>
      <Card>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <form onSubmit={aplicarFiltros} className="flex flex-wrap items-end gap-3">
            <Field label={t("invoices.status")} className="mb-0 w-40">
              <Select value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
                <option value="">{t("invoices.all")}</option>
                <option value="pendiente">{t("invoices.pending")}</option>
                <option value="pagada">{t("invoices.paid")}</option>
                <option value="vencida">{t("invoices.overdue")}</option>
                <option value="anulada">{t("invoices.cancelled")}</option>
              </Select>
            </Field>
            <Field label={t("invoices.from")} className="mb-0">
              <Input type="date" value={filtros.fecha_desde} onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })} />
            </Field>
            <Field label={t("invoices.to")} className="mb-0">
              <Input type="date" value={filtros.fecha_hasta} onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })} />
            </Field>
            <Button type="submit" variant="secondary">
              <Filter size={16} /> {t("invoices.filter")}
            </Button>
          </form>
          <Button onClick={abrirNueva}>
            <Plus size={16} /> {t("invoices.newInvoice")}
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && facturas.length === 0 && (
          <EmptyState title={t("invoices.noInvoices")} description={t("invoices.issueFirstInvoice")} />
        )}

        {!loading && facturas.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} text-left text-xs uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                <th className="py-2">{t("invoices.voucher")}</th>
                <th className="py-2">{t("invoices.client")}</th>
                <th className="py-2">{t("invoices.issueDate")}</th>
                <th className="py-2">{t("invoices.dueDate")}</th>
                <th className="py-2 text-right">{t("invoices.total")}</th>
                <th className="py-2">{t("invoices.status")}</th>
              </tr>
            </thead>
            <tbody>
              {facturas.map((factura) => (
                <tr
                  key={factura.id}
                  onClick={() => navigate(`/facturas/${factura.id}`)}
                  className={`cursor-pointer border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0 ${theme === "dark" ? "hover:bg-ink-800" : "hover:bg-paper-100"}`}
                >
                  <td className={`py-2.5 font-tabular font-medium ${theme === "dark" ? "text-white" : "text-ink-800"}`}>
                    {factura.serie}-{String(factura.numero).padStart(6, "0")}
                  </td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-300" : "text-ink-700"}`}>{factura.cliente_nombre}</td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>{factura.fecha_emision}</td>
                  <td className={`py-2.5 ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>
                    {factura.fecha_vencimiento}
                    {factura.dias_mora > 0 && (
                      <span className={`ml-1 text-xs font-medium ${theme === "dark" ? "text-red-400" : "text-mora-high"}`}>(+{factura.dias_mora}{t("invoices.daysOverdue")})</span>
                    )}
                  </td>
                  <td className={`py-2.5 text-right font-tabular font-medium ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{formatMonto(factura.total)}</td>
                  <td className="py-2.5">
                    <EstadoBadge estado={factura.estado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modalOpen} title={t("invoices.newInvoice")} onClose={() => setModalOpen(false)} widthClass="max-w-2xl">
        <form onSubmit={guardar}>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("invoices.client")}>
              <Select required value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })}>
                <option value="">{t("invoices.selectClient")}</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nombre_razon_social} — {cliente.numero_documento}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("invoices.dueDate")}>
              <Input
                type="date"
                required
                value={form.fecha_vencimiento}
                onChange={(e) => setForm({ ...form, fecha_vencimiento: e.target.value })}
              />
            </Field>
          </div>

          <p className={`mb-2 text-sm font-medium ${theme === "dark" ? "text-white" : "text-ink-700"}`}>{t("invoices.items")}</p>
          <div className="mb-3 flex flex-col gap-2">
            {form.items.map((item, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  className="flex-1"
                  placeholder={t("invoices.description")}
                  required
                  value={item.descripcion}
                  onChange={(e) => actualizarItem(index, "descripcion", e.target.value)}
                />
                <Input
                  className="w-20"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder={t("invoices.quantity")}
                  required
                  value={item.cantidad}
                  onChange={(e) => actualizarItem(index, "cantidad", e.target.value)}
                />
                <Input
                  className="w-28"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder={t("invoices.unitPriceShort")}
                  required
                  value={item.precio_unitario}
                  onChange={(e) => actualizarItem(index, "precio_unitario", e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => quitarItem(index)}
                  disabled={form.items.length === 1}
                  className={`px-2 ${theme === "dark" ? "text-ink-400 hover:text-red-400 disabled:opacity-30" : "text-ink-400 hover:text-mora-high disabled:opacity-30"}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
          <Button type="button" variant="secondary" onClick={agregarItem} className="mb-4">
            <Plus size={14} /> {t("invoices.addItem")}
          </Button>

          <div className={`mb-4 rounded-lg ${theme === "dark" ? "bg-ink-800" : "bg-paper-100"} p-3 text-sm`}>
            <div className={`flex justify-between ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
              <span>{t("invoices.subtotal")}</span>
              <span className="font-tabular">{formatMonto(subtotalEstimado)}</span>
            </div>
            <div className={`flex justify-between ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
              <span>{t("invoices.vat")}</span>
              <span className="font-tabular">{formatMonto(igvEstimado)}</span>
            </div>
            <div className={`mt-1 flex justify-between border-t ${theme === "dark" ? "border-ink-700" : "border-ink-200"} pt-1 font-semibold ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
              <span>{t("invoices.total")}</span>
              <span className="font-tabular">{formatMonto(subtotalEstimado + igvEstimado)}</span>
            </div>
          </div>

          {error && <p className="mb-3 text-sm text-mora-high">{error}</p>}

          {riskAlert && (
            <div className={`mb-3 rounded-lg p-3 ${theme === "dark" ? "bg-red-900/20 border border-red-800" : "bg-red-50 border border-red-200"}`}>
              <div className="flex items-start gap-2">
                <span className="text-lg">⚠️</span>
                <div className="flex-1">
                  <p className={`font-medium ${theme === "dark" ? "text-red-400" : "text-red-800"}`}>
                    {riskAlert.mensaje}
                  </p>
                  <div className={`mt-2 text-xs ${theme === "dark" ? "text-red-300" : "text-red-700"}`}>
                    <p><strong>Nivel de riesgo:</strong> {riskAlert.nivel}</p>
                    <p><strong>Score:</strong> {(riskAlert.score * 100).toFixed(0)}%</p>
                    <p><strong>Factores:</strong></p>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>% Facturas vencidas: {(riskAlert.factores.pct_facturas_vencidas * 100).toFixed(1)}%</li>
                      <li>% Pagos tardíos: {(riskAlert.factores.pct_pagos_tardios * 100).toFixed(1)}%</li>
                      <li>Días mora promedio: {riskAlert.factores.dias_mora_promedio.toFixed(1)} días</li>
                    </ul>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setRiskAlert(null)}>
                  Editar factura
                </Button>
                <Button variant="primary" size="sm" onClick={confirmarConRiesgo}>
                  Confirmar de todas formas
                </Button>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? t("invoices.issuing") : t("invoices.newInvoice")}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
