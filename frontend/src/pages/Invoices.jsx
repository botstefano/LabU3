import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, Filter } from "lucide-react";
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
      setModalOpen(false);
      cargarFacturas();
      navigate(`/facturas/${res.data.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "No se pudo emitir la factura");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <AppLayout title="Facturación">
      <Card>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <form onSubmit={aplicarFiltros} className="flex flex-wrap items-end gap-3">
            <Field label="Estado" className="mb-0 w-40">
              <Select value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
                <option value="">Todos</option>
                <option value="pendiente">Pendiente</option>
                <option value="pagada">Pagada</option>
                <option value="vencida">Vencida</option>
                <option value="anulada">Anulada</option>
              </Select>
            </Field>
            <Field label="Desde" className="mb-0">
              <Input type="date" value={filtros.fecha_desde} onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })} />
            </Field>
            <Field label="Hasta" className="mb-0">
              <Input type="date" value={filtros.fecha_hasta} onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })} />
            </Field>
            <Button type="submit" variant="secondary">
              <Filter size={16} /> Filtrar
            </Button>
          </form>
          <Button onClick={abrirNueva}>
            <Plus size={16} /> Nueva factura
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && facturas.length === 0 && (
          <EmptyState title="No hay facturas emitidas" description="Emite tu primera factura electrónica para comenzar." />
        )}

        {!loading && facturas.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                <th className="py-2">Comprobante</th>
                <th className="py-2">Cliente</th>
                <th className="py-2">Emisión</th>
                <th className="py-2">Vencimiento</th>
                <th className="py-2 text-right">Total</th>
                <th className="py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {facturas.map((factura) => (
                <tr
                  key={factura.id}
                  onClick={() => navigate(`/facturas/${factura.id}`)}
                  className="cursor-pointer border-b border-ink-100 last:border-0 hover:bg-paper-100"
                >
                  <td className="py-2.5 font-tabular font-medium text-ink-800">
                    {factura.serie}-{String(factura.numero).padStart(6, "0")}
                  </td>
                  <td className="py-2.5 text-ink-700">{factura.cliente_nombre}</td>
                  <td className="py-2.5 text-ink-500">{factura.fecha_emision}</td>
                  <td className="py-2.5 text-ink-500">
                    {factura.fecha_vencimiento}
                    {factura.dias_mora > 0 && (
                      <span className="ml-1 text-xs font-medium text-mora-high">(+{factura.dias_mora}d)</span>
                    )}
                  </td>
                  <td className="py-2.5 text-right font-tabular font-medium text-ink-900">{formatMonto(factura.total)}</td>
                  <td className="py-2.5">
                    <EstadoBadge estado={factura.estado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva factura" onClose={() => setModalOpen(false)} widthClass="max-w-2xl">
        <form onSubmit={guardar}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Cliente">
              <Select required value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })}>
                <option value="">Seleccione un cliente</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nombre_razon_social} — {cliente.numero_documento}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fecha de vencimiento">
              <Input
                type="date"
                required
                value={form.fecha_vencimiento}
                onChange={(e) => setForm({ ...form, fecha_vencimiento: e.target.value })}
              />
            </Field>
          </div>

          <p className="mb-2 text-sm font-medium text-ink-700">Detalle de la factura</p>
          <div className="mb-3 flex flex-col gap-2">
            {form.items.map((item, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  className="flex-1"
                  placeholder="Descripción"
                  required
                  value={item.descripcion}
                  onChange={(e) => actualizarItem(index, "descripcion", e.target.value)}
                />
                <Input
                  className="w-20"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="Cant."
                  required
                  value={item.cantidad}
                  onChange={(e) => actualizarItem(index, "cantidad", e.target.value)}
                />
                <Input
                  className="w-28"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="Precio"
                  required
                  value={item.precio_unitario}
                  onChange={(e) => actualizarItem(index, "precio_unitario", e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => quitarItem(index)}
                  disabled={form.items.length === 1}
                  className="px-2 text-ink-400 hover:text-mora-high disabled:opacity-30"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
          <Button type="button" variant="secondary" onClick={agregarItem} className="mb-4">
            <Plus size={14} /> Agregar ítem
          </Button>

          <div className="mb-4 rounded-lg bg-paper-100 p-3 text-sm">
            <div className="flex justify-between text-ink-600">
              <span>Subtotal estimado</span>
              <span className="font-tabular">{formatMonto(subtotalEstimado)}</span>
            </div>
            <div className="flex justify-between text-ink-600">
              <span>IGV estimado (18%)</span>
              <span className="font-tabular">{formatMonto(igvEstimado)}</span>
            </div>
            <div className="mt-1 flex justify-between border-t border-ink-200 pt-1 font-semibold text-ink-900">
              <span>Total estimado</span>
              <span className="font-tabular">{formatMonto(subtotalEstimado + igvEstimado)}</span>
            </div>
          </div>

          {error && <p className="mb-3 text-sm text-mora-high">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Emitiendo..." : "Emitir factura"}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
