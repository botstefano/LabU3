import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, Ban } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import EstadoBadge from "../components/ui/EstadoBadge";
import { LoadingState, ErrorState } from "../components/ui/States";
import { invoiceService } from "../services/invoiceService";
import { useAuth } from "../context/AuthContext";

function formatMonto(valor) {
  return `S/ ${Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [factura, setFactura] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const cargar = () => {
    setLoading(true);
    invoiceService
      .get(id)
      .then((res) => setFactura(res.data))
      .catch(() => setError("No se pudo cargar la factura"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const descargarPdf = async () => {
    const res = await invoiceService.descargarPdf(id);
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${factura.serie}-${String(factura.numero).padStart(6, "0")}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const anular = async () => {
    if (!confirm("¿Está seguro de anular esta factura? Esta acción no se puede revertir.")) return;
    await invoiceService.anular(id);
    cargar();
  };

  const puedeAnular = ["administrador", "contador"].includes(user?.rol);

  return (
    <AppLayout title="Detalle de factura">
      <button onClick={() => navigate("/facturas")} className="mb-4 flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-800">
        <ArrowLeft size={16} /> Volver a facturación
      </button>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {factura && (
        <div className="flex flex-col gap-6">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="font-tabular text-2xl font-semibold text-ink-900">
                  {factura.serie}-{String(factura.numero).padStart(6, "0")}
                </p>
                <div className="mt-1"><EstadoBadge estado={factura.estado} /></div>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={descargarPdf}>
                  <Download size={16} /> Descargar PDF
                </Button>
                {puedeAnular && factura.estado !== "anulada" && factura.estado !== "pagada" && (
                  <Button variant="danger" onClick={anular}>
                    <Ban size={16} /> Anular
                  </Button>
                )}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              <div>
                <p className="text-xs uppercase text-ink-400">Cliente</p>
                <p className="font-medium text-ink-800">{factura.client.nombre_razon_social}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-ink-400">Documento</p>
                <p className="text-ink-700">{factura.client.tipo_documento} {factura.client.numero_documento}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-ink-400">Emisión</p>
                <p className="text-ink-700">{factura.fecha_emision}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-ink-400">Vencimiento</p>
                <p className="text-ink-700">
                  {factura.fecha_vencimiento}
                  {factura.dias_mora > 0 && <span className="ml-1 text-mora-high">(+{factura.dias_mora}d de mora)</span>}
                </p>
              </div>
            </div>
          </Card>

          <Card title="Detalle de ítems">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                  <th className="py-2">Descripción</th>
                  <th className="py-2 text-right">Cantidad</th>
                  <th className="py-2 text-right">Precio unit.</th>
                  <th className="py-2 text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {factura.items.map((item) => (
                  <tr key={item.id} className="border-b border-ink-100 last:border-0">
                    <td className="py-2.5 text-ink-800">{item.descripcion}</td>
                    <td className="py-2.5 text-right font-tabular text-ink-600">{item.cantidad}</td>
                    <td className="py-2.5 text-right font-tabular text-ink-600">{formatMonto(item.precio_unitario)}</td>
                    <td className="py-2.5 text-right font-tabular font-medium text-ink-900">{formatMonto(item.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="ml-auto mt-4 w-full max-w-xs text-sm">
              <div className="flex justify-between py-1 text-ink-600">
                <span>Subtotal</span>
                <span className="font-tabular">{formatMonto(factura.subtotal)}</span>
              </div>
              <div className="flex justify-between py-1 text-ink-600">
                <span>IGV</span>
                <span className="font-tabular">{formatMonto(factura.igv)}</span>
              </div>
              <div className="flex justify-between border-t border-ink-200 py-1.5 font-semibold text-ink-900">
                <span>Total</span>
                <span className="font-tabular">{formatMonto(factura.total)}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </AppLayout>
  );
}
