
import { useEffect, useState, useRef } from "react";
import { BrainCircuit, RefreshCw, Upload, BarChart3, TrendingUp, AlertCircle } from "lucide-react";
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

function ProgressBar({ progress, currentStep }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-ink-600">{currentStep}</span>
        <span className="font-medium text-ink-900">{(progress * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-ink-100 rounded-full overflow-hidden">
        <div 
          className="h-full bg-brand-500 transition-all duration-300 ease-out"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </div>
  );
}

function EDACard({ eda }) {
  if (!eda) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-xs text-blue-600 uppercase tracking-wide">Muestras</p>
          <p className="text-2xl font-bold text-blue-900">{eda.n_muestras}</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3">
          <p className="text-xs text-red-600 uppercase tracking-wide">Alto Riesgo</p>
          <p className="text-2xl font-bold text-red-900">{eda.n_clase_alto_riesgo}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3">
          <p className="text-xs text-green-600 uppercase tracking-wide">Bajo Riesgo</p>
          <p className="text-2xl font-bold text-green-900">{eda.n_clase_bajo_riesgo}</p>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-medium text-ink-900 mb-2">Estadísticas de Features</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-ink-200">
                <th className="text-left py-2 pr-2">Feature</th>
                <th className="text-right py-2 px-2">Media</th>
                <th className="text-right py-2 px-2">Std</th>
                <th className="text-right py-2 px-2">Min</th>
                <th className="text-right py-2 px-2">Max</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(eda.feature_stats).map(([name, stats]) => (
                <tr key={name} className="border-b border-ink-100 last:border-0">
                  <td className="py-2 pr-2 text-ink-700">{name}</td>
                  <td className="py-2 px-2 text-right font-tabular">{stats.mean.toFixed(3)}</td>
                  <td className="py-2 px-2 text-right font-tabular">{stats.std.toFixed(3)}</td>
                  <td className="py-2 px-2 text-right font-tabular">{stats.min.toFixed(3)}</td>
                  <td className="py-2 px-2 text-right font-tabular">{stats.max.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricsCard({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-brand-50 rounded-lg p-3">
          <p className="text-xs text-brand-600 uppercase tracking-wide">Accuracy</p>
          <p className="text-2xl font-bold text-brand-900">{(metrics.accuracy * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3">
          <p className="text-xs text-purple-600 uppercase tracking-wide">Precision</p>
          <p className="text-2xl font-bold text-purple-900">{(metrics.precision * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-indigo-50 rounded-lg p-3">
          <p className="text-xs text-indigo-600 uppercase tracking-wide">Recall</p>
          <p className="text-2xl font-bold text-indigo-900">{(metrics.recall * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-pink-50 rounded-lg p-3">
          <p className="text-xs text-pink-600 uppercase tracking-wide">F1 Score</p>
          <p className="text-2xl font-bold text-pink-900">{(metrics.f1 * 100).toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-ink-900 mb-2">Matriz de Confusión</h4>
          <div className="bg-ink-50 rounded-lg p-4">
            <table className="w-full text-sm">
              <tbody>
                {metrics.confusion_matrix.map((row, i) => (
                  <tr key={i}>
                    {row.map((val, j) => (
                      <td key={j} className={`py-2 px-3 text-center rounded ${val > 0 ? 'bg-white font-medium' : 'bg-ink-100 text-ink-400'}`}>
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex justify-between text-xs text-ink-500 mt-2 px-3">
              <span>Pred: Bajo</span>
              <span>Pred: Alto</span>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-ink-900 mb-2">Importancia de Features</h4>
          <div className="space-y-2">
            {Object.entries(metrics.feature_importance)
              .sort(([, a], [, b]) => b - a)
              .map(([name, importance]) => (
                <div key={name} className="flex items-center gap-2">
                  <span className="text-xs text-ink-600 w-32 truncate">{name}</span>
                  <div className="flex-1 h-4 bg-ink-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-brand-500"
                      style={{ width: `${importance}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-ink-900 w-12 text-right">{importance.toFixed(1)}%</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Risk() {
  const { user } = useAuth();
  const [clients, setClients] = useState(null);
  const [trainResult, setTrainResult] = useState(null);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

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

  const loadTrainingStatus = () => {
    riskService
      .getTrainingStatus()
      .then((res) => {
        setTrainingStatus(res.data);
        if (res.data.result) {
          setTrainResult(res.data.result);
        }
        if (res.data.status === "completed" || res.data.status === "error") {
          setTraining(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          if (res.data.status === "completed" && res.data.result?.entrenado) {
            loadClients();
          }
        }
      })
      .catch(() => {});
  };

  const startPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    pollingRef.current = setInterval(loadTrainingStatus, 1000);
  };

  const handleTrain = () => {
    setTraining(true);
    setError("");
    setTrainResult(null);
    riskService
      .train()
      .then(() => {
        startPolling();
      })
      .catch(() => {
        setError("No se pudo entrenar el modelo");
        setTraining(false);
      });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadFile(file);
    }
  };

  const handleUploadDataset = () => {
    if (!uploadFile) return;

    setTraining(true);
    setError("");
    setTrainResult(null);
    riskService
      .uploadDataset(uploadFile)
      .then(() => {
        startPolling();
        setUploadFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      })
      .catch(() => {
        setError("No se pudo cargar el dataset");
        setTraining(false);
      });
  };

  useEffect(() => {
    loadClients();
    loadTrainingStatus();

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  return (
    <AppLayout title="Riesgo de Morosidad">
      <div className="flex flex-col gap-6">
        {canTrain && (
          <>
            <Card title="Cargar Dataset de Entrenamiento">
              <div className="flex flex-col gap-4">
                <p className="text-sm text-ink-600">
                  Sube un archivo CSV o JSON con datos históricos para entrenar el modelo.
                  El archivo debe contener las columnas: pct_facturas_vencidas, pct_pagos_tardios, 
                  dias_mora_promedio, monto_promedio_factura, cantidad_facturas, antiguedad_dias, label.
                </p>
                <div className="flex gap-3 items-center">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.json"
                    onChange={handleFileUpload}
                    className="block w-full text-sm text-ink-600
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-medium
                      file:bg-brand-50 file:text-brand-700
                      hover:file:bg-brand-100"
                  />
                  <Button 
                    onClick={handleUploadDataset} 
                    disabled={!uploadFile || training}
                    variant="primary"
                  >
                    <Upload size={16} className="mr-2" />
                    Entrenar con Dataset
                  </Button>
                </div>
              </div>
            </Card>

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
                      <BrainCircuit size={16} /> Entrenar con BD
                    </>
                  )}
                </Button>
              }
            >
              <p className="text-sm text-ink-600">
                El modelo se entrena localmente con scikit-learn. No se envía información a servicios externos.
              </p>

              {training && trainingStatus && (
                <div className="mt-4 p-4 bg-ink-50 rounded-lg">
                  <ProgressBar progress={trainingStatus.progress} currentStep={trainingStatus.current_step} />
                  {trainingStatus.mensaje && (
                    <p className="text-sm text-ink-600 mt-2">{trainingStatus.mensaje}</p>
                  )}
                </div>
              )}

              {trainResult && !training && (
                <div className={`mt-4 rounded-lg p-4 ${trainResult.entrenado ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-800"}`}>
                  <div className="flex items-start gap-2">
                    {trainResult.entrenado ? (
                      <TrendingUp size={20} className="mt-0.5" />
                    ) : (
                      <AlertCircle size={20} className="mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium">{trainResult.mensaje}</p>
                      <p className="text-sm mt-1">Muestras: {trainResult.n_muestras} | Alto riesgo: {trainResult.n_clase_alto_riesgo}</p>
                      <p className="text-sm mt-1">Modelo disponible: {trainResult.modelo_disponible ? "Sí" : "No"}</p>
                    </div>
                  </div>
                </div>
              )}

              {trainResult?.eda && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-ink-900 mb-3 flex items-center gap-2">
                    <BarChart3 size={16} />
                    Análisis Exploratorio de Datos (EDA)
                  </h3>
                  <EDACard eda={trainResult.eda} />
                </div>
              )}

              {trainResult?.metrics && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-ink-900 mb-3 flex items-center gap-2">
                    <TrendingUp size={16} />
                    Métricas de Evaluación
                  </h3>
                  <MetricsCard metrics={trainResult.metrics} />
                </div>
              )}
            </Card>
          </>
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

