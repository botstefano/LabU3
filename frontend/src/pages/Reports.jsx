import { useState } from "react";
import { FileSpreadsheet, FileText } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { Field, Input, Select } from "../components/ui/FormElements";
import { reportsService } from "../services/reportsService";

function descargarBlob(data, filename, mimeType) {
  const url = window.URL.createObjectURL(new Blob([data], { type: mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

export default function Reports() {
  const [filtros, setFiltros] = useState({ fecha_desde: "", fecha_hasta: "", estado: "" });
  const [descargando, setDescargando] = useState("");

  const construirParams = () => {
    const params = {};
    if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde;
    if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta;
    if (filtros.estado) params.estado = filtros.estado;
    return params;
  };

  const exportarExcel = async () => {
    setDescargando("excel");
    try {
      const res = await reportsService.descargarExcel(construirParams());
      descargarBlob(res.data, "reporte_facturacion.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    } finally {
      setDescargando("");
    }
  };

  const exportarPdf = async () => {
    setDescargando("pdf");
    try {
      const res = await reportsService.descargarPdf(construirParams());
      descargarBlob(res.data, "reporte_facturacion.pdf", "application/pdf");
    } finally {
      setDescargando("");
    }
  };

  return (
    <AppLayout title="Reportes">
      <Card title="Reporte de facturación" className="max-w-2xl">
        <p className="mb-4 text-sm text-ink-500">
          Genera un reporte exportable de las facturas emitidas, filtrando por rango de fechas y estado del
          comprobante.
        </p>

        <div className="grid grid-cols-3 gap-3">
          <Field label="Desde">
            <Input type="date" value={filtros.fecha_desde} onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })} />
          </Field>
          <Field label="Hasta">
            <Input type="date" value={filtros.fecha_hasta} onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })} />
          </Field>
          <Field label="Estado">
            <Select value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
              <option value="">Todos</option>
              <option value="pendiente">Pendiente</option>
              <option value="pagada">Pagada</option>
              <option value="vencida">Vencida</option>
              <option value="anulada">Anulada</option>
            </Select>
          </Field>
        </div>

        <div className="mt-4 flex gap-3">
          <Button variant="secondary" onClick={exportarExcel} disabled={descargando === "excel"}>
            <FileSpreadsheet size={16} /> {descargando === "excel" ? "Generando..." : "Exportar a Excel"}
          </Button>
          <Button variant="secondary" onClick={exportarPdf} disabled={descargando === "pdf"}>
            <FileText size={16} /> {descargando === "pdf" ? "Generando..." : "Exportar a PDF"}
          </Button>
        </div>
      </Card>
    </AppLayout>
  );
}
