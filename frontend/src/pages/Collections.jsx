import { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState, EmptyState } from "../components/ui/States";
import { collectionsService } from "../services/collectionsService";

function formatMonto(valor) {
  return `S/ ${Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

function claseMora(dias) {
  if (dias > 60) return "text-mora-high";
  if (dias > 30) return "text-mora-mid";
  return "text-mora-low";
}

export default function Collections() {
  const [cartera, setCartera] = useState([]);
  const [segmentos, setSegmentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [facturaSeleccionada, setFacturaSeleccionada] = useState(null);
  const [monto, setMonto] = useState("");
  const [metodoPago, setMetodoPago] = useState("transferencia");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = async () => {
    setLoading(true);
    try {
      const [carteraRes, segmentosRes] = await Promise.all([
        collectionsService.cartera(),
        collectionsService.segmentos(),
      ]);
      setCartera(carteraRes.data);
      setSegmentos(segmentosRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const abrirPago = (factura) => {
    setFacturaSeleccionada(factura);
    setMonto(factura.saldo_pendiente.toFixed(2));
    setMetodoPago("transferencia");
    setError("");
    setModalOpen(true);
  };

  const registrarPago = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setError("");
    try {
      await collectionsService.registrarPago({
        invoice_id: facturaSeleccionada.id,
        monto: Number(monto),
        metodo_pago: metodoPago,
      });
      setModalOpen(false);
      cargar();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "No se pudo registrar el pago");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <AppLayout title="Cobranzas y morosidad">
      <div className="flex flex-col gap-6">
        <Card title="Segmentación de deuda por antigüedad">
          {loading ? (
            <LoadingState />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {segmentos.map((segmento) => (
                <div key={segmento.segmento} className="rounded-lg border border-ink-100 p-3">
                  <p className="text-xs uppercase tracking-wide text-ink-400">{segmento.segmento}</p>
                  <p className="mt-1 font-tabular text-lg font-semibold text-ink-900">
                    {formatMonto(segmento.monto_total)}
                  </p>
                  <p className="text-xs text-ink-500">{segmento.cantidad_facturas} factura(s)</p>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Cartera vencida">
          {loading && <LoadingState />}
          {!loading && cartera.length === 0 && (
            <EmptyState title="No hay facturas en mora" description="Todas las facturas están al día." />
          )}
          {!loading && cartera.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                  <th className="py-2">Comprobante</th>
                  <th className="py-2">Cliente</th>
                  <th className="py-2">Vencimiento</th>
                  <th className="py-2 text-right">Días de mora</th>
                  <th className="py-2 text-right">Saldo pendiente</th>
                  <th className="py-2 text-right">Acción</th>
                </tr>
              </thead>
              <tbody>
                {cartera.map((factura) => (
                  <tr key={factura.id} className="border-b border-ink-100 last:border-0">
                    <td className="py-2.5 font-tabular font-medium text-ink-800">
                      {factura.serie}-{String(factura.numero).padStart(6, "0")}
                    </td>
                    <td className="py-2.5 text-ink-700">{factura.cliente_nombre}</td>
                    <td className="py-2.5 text-ink-500">{factura.fecha_vencimiento}</td>
                    <td className={`py-2.5 text-right font-tabular font-semibold ${claseMora(factura.dias_mora)}`}>
                      {factura.dias_mora}
                    </td>
                    <td className="py-2.5 text-right font-tabular font-medium text-ink-900">
                      {formatMonto(factura.saldo_pendiente)}
                    </td>
                    <td className="py-2.5 text-right">
                      <Button variant="secondary" onClick={() => abrirPago(factura)}>
                        <CreditCard size={14} /> Registrar pago
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <Modal open={modalOpen} title="Registrar pago" onClose={() => setModalOpen(false)}>
        {facturaSeleccionada && (
          <form onSubmit={registrarPago}>
            <p className="mb-4 text-sm text-ink-600">
              Comprobante <span className="font-tabular font-medium text-ink-900">
                {facturaSeleccionada.serie}-{String(facturaSeleccionada.numero).padStart(6, "0")}
              </span>{" "}
              — Saldo pendiente:{" "}
              <span className="font-tabular font-medium text-ink-900">
                {formatMonto(facturaSeleccionada.saldo_pendiente)}
              </span>
            </p>
            <Field label="Monto a pagar">
              <Input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
              />
            </Field>
            <Field label="Método de pago">
              <Select value={metodoPago} onChange={(e) => setMetodoPago(e.target.value)}>
                <option value="transferencia">Transferencia</option>
                <option value="efectivo">Efectivo</option>
                <option value="tarjeta">Tarjeta</option>
                <option value="deposito">Depósito</option>
              </Select>
            </Field>

            {error && <p className="mb-3 text-sm text-mora-high">{error}</p>}

            <div className="flex justify-end gap-2">
              <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={guardando}>
                {guardando ? "Registrando..." : "Registrar pago"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </AppLayout>
  );
}
