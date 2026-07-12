
import { useEffect, useState } from "react";
import { BrainCircuit, RefreshCw } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { LoadingState, ErrorState, EmptyState } from "../components/ui/States";
import { riskService } from "../services/riskService";
import { useAuth } from "../context/AuthContext";

function RiskBadge({ nivel }) {
  const styles = {
    bajo: "bg-green-100 text-green-700",
    medio: "bg-amber-100 text-amber-700",
    alto: "bg-red-100 text-red-700",
  };
  const labels = {
    bajo: "Bajo",
    medio: "Medio",
    alto: "Alto",
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[nivel]}`}>
      {labels[nivel]}
    </span>
  );
}

export default function Risk() {
  const { user } = useAuth();
  const [clients, setClients] = useState(null);
  const [trainResult, setTrainResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);

  const canTrain = user?.rol === "administrador" || user?.rol === "contador";

  const loadClients = () => {
    setLoading(true);
    setError("");
    riskService
      .listClients()
      .then((res) => setClients(res.data))
      .catch(() => setError("No se pudo cargar la información de riesgo"))
      .finally(() => setLoading(false));
  };

  const handleTrain = () => {
    setTraining(true);
    setError("");
    riskService
      .train()
      .then((res) => {
        setTrainResult(res.data);
        loadClients();
      })
      .catch(() => setError("No se pudo entrenar el modelo"))
      .finally(() => setTraining(false));
  };

  useEffect(() => {
    loadClients();
  }, []);

  return (
    <AppLayout title="Riesgo de Morosidad">
      <div className="flex flex-col gap-6">
        {canTrain && (
          <Card
            title="Entrenamiento del Modelo"
            action={
              <Button onClick={handleTrain} disabled={training} variant="primary">
                {training ? (
                  <>
                    <RefreshCw className="animate-spin" size={16} /> Entrenando...
                  </>
                ) : (
                  <>
                    <BrainCircuit size={16} /> Entrenar Modelo
                  </>
                )}
              </Button>
            }
          >
            <p className="text-sm text-ink-600">
              El modelo se entrena localmente con los datos históricos de facturas y pagos de tus clientes.
              No se envía información a servicios externos.
            </p>
            {trainResult && (
              <div className={`mt-4 rounded-lg p-4 ${trainResult.entrenado ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-800"}`}>
                <p className="font-medium">{trainResult.mensaje}</p>
                <p className="text-sm mt-1">Muestras: {trainResult.n_muestras} | Alto riesgo: {trainResult.n_clase_alto_riesgo}</p>
                {trainResult.accuracy !== null && (
                  <p className="text-sm mt-1">Exactitud: {(trainResult.accuracy * 100).toFixed(1)}% | F1: {(trainResult.f1 * 100).toFixed(1)}%</p>
                )}
                <p className="text-sm mt-1">Modelo disponible: {trainResult.modelo_disponible ? "Sí" : "No"}</p>
              </div>
            )}
          </Card>
        )}

        <Card title="Clientes por Riesgo de Morosidad">
          {loading && <LoadingState />}
          {error && <ErrorState message={error} />}

          {!loading && !error && clients && (
            <>
              {clients.length === 0 ? (
                <EmptyState title="Sin clientes" description="No hay clientes registrados aún" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                        <th className="py-3 pr-4">Cliente</th>
                        <th className="py-3 px-4 text-right">Score</th>
                        <th className="py-3 px-4">Nivel</th>
                        <th className="py-3 px-4">Método</th>
                        <th className="py-3 px-4 text-right">% Facturas Vencidas</th>
                        <th className="py-3 pl-4 text-right">Días Mora Promedio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clients.map((client) => (
                        <tr key={client.client_id} className="border-b border-ink-100 last:border-0">
                          <td className="py-3 pr-4 text-ink-800">{client.cliente_nombre}</td>
                          <td className="py-3 px-4 text-right font-tabular font-medium text-ink-900">
                            {(client.score * 100).toFixed(1)}%
                          </td>
                          <td className="py-3 px-4">
                            <RiskBadge nivel={client.nivel} />
                          </td>
                          <td className="py-3 px-4 text-ink-600 capitalize">
                            {client.metodo === "sin_historial" ? "Sin historial" : client.metodo}
                          </td>
                          <td className="py-3 px-4 text-right font-tabular text-ink-600">
                            {client.factores ? `${(client.factores.pct_facturas_vencidas * 100).toFixed(1)}%` : "-"}
                          </td>
                          <td className="py-3 pl-4 text-right font-tabular text-ink-600">
                            {client.factores ? client.factores.dias_mora_promedio.toFixed(1) : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}

