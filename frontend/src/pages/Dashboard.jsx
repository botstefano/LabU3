import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { TrendingUp, Receipt, AlertTriangle, FileWarning } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import { LoadingState, ErrorState } from "../components/ui/States";
import { dashboardService } from "../services/dashboardService";

function formatMonto(valor) {
  return `S/ ${Number(valor).toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

function MetricCard({ icon: Icon, label, value, accent }) {
  const { theme } = useTheme();
  
  return (
    <Card className="flex items-center gap-4">
      <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${accent}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className={`text-xs font-medium uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>{label}</p>
        <p className={`font-tabular text-lg font-semibold ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{value}</p>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const { t } = useTranslation();
  const { theme } = useTheme();

  useEffect(() => {
    dashboardService
      .resumen()
      .then((res) => setData(res.data))
      .catch(() => setError(t("common.unexpectedError")))
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <AppLayout title={t("dashboard.title")}>
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {data && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              icon={Receipt}
              label={t("dashboard.invoiced")}
              value={formatMonto(data.total_facturado_mes_actual)}
              accent="bg-brand-100 text-brand-700"
            />
            <MetricCard
              icon={TrendingUp}
              label={t("dashboard.vatCollected")}
              value={formatMonto(data.igv_recaudado_mes_actual)}
              accent="bg-ink-100 text-ink-700"
            />
            <MetricCard
              icon={AlertTriangle}
              label={t("dashboard.totalDelinquency")}
              value={formatMonto(data.total_morosidad)}
              accent="bg-red-100 text-mora-high"
            />
            <MetricCard
              icon={FileWarning}
              label={t("dashboard.pendingInvoices")}
              value={data.cantidad_facturas_pendientes}
              accent="bg-amber-100 text-amber-700"
            />
          </div>

          <Card title={t("dashboard.monthlyInvoicing")}>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.facturacion_mensual}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme === "dark" ? "#334155" : "#E2E8F0"} />
                  <XAxis dataKey="mes" tick={{ fontSize: 12 }} stroke={theme === "dark" ? "#94A3B8" : "#64748B"} />
                  <YAxis tick={{ fontSize: 12 }} stroke={theme === "dark" ? "#94A3B8" : "#64748B"} />
                  <Tooltip formatter={(value) => formatMonto(value)} />
                  <Bar dataKey="total_facturado" name={t("dashboard.invoiced")} fill="#0D9488" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="igv_recaudado" name={t("dashboard.vatCollected")} fill={theme === "dark" ? "#94A3B8" : "#0F172A"} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title={t("dashboard.topClients")}>
            <table className="w-full text-sm">
              <thead>
                <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} text-left text-xs uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                  <th className="py-2">{t("dashboard.client")}</th>
                  <th className="py-2 text-right">{t("dashboard.invoices")}</th>
                  <th className="py-2 text-right">{t("dashboard.totalPurchased")}</th>
                </tr>
              </thead>
              <tbody>
                {data.top_clientes.map((cliente) => (
                  <tr key={cliente.cliente_nombre} className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0`}>
                    <td className={`py-2.5 ${theme === "dark" ? "text-white" : "text-ink-800"}`}>{cliente.cliente_nombre}</td>
                    <td className={`py-2.5 text-right font-tabular ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>{cliente.cantidad_facturas}</td>
                    <td className={`py-2.5 text-right font-tabular font-medium ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                      {formatMonto(cliente.total_comprado)}
                    </td>
                  </tr>
                ))}
                {data.top_clientes.length === 0 && (
                  <tr>
                    <td colSpan={3} className={`py-6 text-center ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                      {t("dashboard.noInvoicesYet")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </AppLayout>
  );
}
