import { useEffect, useState, useRef } from "react";
import { BrainCircuit, RefreshCw, Upload, BarChart3, TrendingUp, AlertCircle } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { LoadingState, ErrorState, EmptyState } from "../components/ui/States";
import { riskService } from "../services/riskService";
import { invoiceService } from "../services/invoiceService";
import { useAuth } from "../context/AuthContext";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";

function RiskBadge({ nivel }) {
  const styles = {
    bajo: "bg-green-100 text-green-700",
    medio: "bg-amber-100 text-amber-700",
    alto: "bg-red-100 text-red-700",
  };
  const { t } = useTranslation();
  const labels = {
    bajo: t("risk.low"),
    medio: t("risk.medium"),
    alto: t("risk.high"),
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
  const { t } = useTranslation();
  const { theme } = useTheme();

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-blue-900/20" : "bg-blue-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-blue-400" : "text-blue-600"}`}>{t("risk.samples")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-blue-300" : "text-blue-900"}`}>{eda.n_muestras}</p>
        </div>
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-red-900/20" : "bg-red-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-red-400" : "text-red-600"}`}>{t("risk.highRisk")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-red-300" : "text-red-900"}`}>{eda.n_clase_alto_riesgo}</p>
        </div>
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-green-900/20" : "bg-green-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-green-400" : "text-green-600"}`}>{t("risk.lowRisk")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-green-300" : "text-green-900"}`}>{eda.n_clase_bajo_riesgo}</p>
        </div>
      </div>

      <div>
        <h4 className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{t("risk.features")}</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-200"}`}>
                <th className={`text-left py-2 pr-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>{t("risk.features")}</th>
                <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>{t("risk.mean")}</th>
                <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>{t("risk.std")}</th>
                <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>{t("risk.min")}</th>
                <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>{t("risk.max")}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(eda.feature_stats).map(([name, stats]) => (
                <tr key={name} className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0`}>
                  <td className={`py-2 pr-2 ${theme === "dark" ? "text-ink-300" : "text-ink-700"}`}>{name}</td>
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
  const { t } = useTranslation();
  const { theme } = useTheme();

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-brand-900/20" : "bg-brand-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-brand-400" : "text-brand-600"}`}>{t("risk.accuracy")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-brand-300" : "text-brand-900"}`}>{(metrics.accuracy * 100).toFixed(1)}%</p>
        </div>
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-purple-900/20" : "bg-purple-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-purple-400" : "text-purple-600"}`}>{t("risk.precision")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-purple-300" : "text-purple-900"}`}>{(metrics.precision * 100).toFixed(1)}%</p>
        </div>
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-indigo-900/20" : "bg-indigo-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-indigo-400" : "text-indigo-600"}`}>{t("risk.recall")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-indigo-300" : "text-indigo-900"}`}>{(metrics.recall * 100).toFixed(1)}%</p>
        </div>
        <div className={`rounded-lg p-3 ${theme === "dark" ? "bg-pink-900/20" : "bg-pink-50"}`}>
          <p className={`text-xs uppercase tracking-wide ${theme === "dark" ? "text-pink-400" : "text-pink-600"}`}>{t("risk.f1")}</p>
          <p className={`text-2xl font-bold ${theme === "dark" ? "text-pink-300" : "text-pink-900"}`}>{(metrics.f1 * 100).toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{t("risk.confusionMatrix")}</h4>
          <div className={`rounded-lg p-4 ${theme === "dark" ? "bg-ink-800" : "bg-ink-50"}`}>
            <table className="w-full text-sm">
              <tbody>
                {metrics.confusion_matrix.map((row, i) => (
                  <tr key={i}>
                    {row.map((val, j) => (
                      <td key={j} className={`py-2 px-3 text-center rounded ${val > 0 ? (theme === "dark" ? "bg-ink-700 font-medium text-white" : "bg-white font-medium text-ink-900") : (theme === "dark" ? "bg-ink-800 text-ink-400" : "bg-ink-100 text-ink-400")}`}>
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className={`flex justify-between text-xs mt-2 px-3 ${theme === "dark" ? "text-ink-400" : "text-ink-500"}`}>
              <span>Pred: {t("risk.low")}</span>
              <span>Pred: {t("risk.high")}</span>
            </div>
          </div>
        </div>

        <div>
          <h4 className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{t("risk.featureImportance")}</h4>
          <div className="space-y-2">
            {Object.entries(metrics.feature_importance)
              .sort(([, a], [, b]) => b - a)
              .map(([name, importance]) => (
                <div key={name} className="flex items-center gap-2">
                  <span className={`text-xs w-32 truncate ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>{name}</span>
                  <div className={`flex-1 h-4 rounded-full overflow-hidden ${theme === "dark" ? "bg-ink-800" : "bg-ink-100"}`}>
                    <div
                      className="h-full bg-brand-500"
                      style={{ width: `${importance}%` }}
                    />
                  </div>
                  <span className={`text-xs font-medium w-12 text-right ${theme === "dark" ? "text-white" : "text-ink-900"}`}>{importance.toFixed(1)}%</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function CorrelationHeatmap({ correlationMatrix, theme }) {
  if (!correlationMatrix) return null;
  
  const featureNames = Object.keys(correlationMatrix);
  const colors = {
    positive: theme === "dark" ? "rgba(239, 68, 68, 0.8)" : "rgba(239, 68, 68, 0.7)",
    negative: theme === "dark" ? "rgba(59, 130, 246, 0.8)" : "rgba(59, 130, 246, 0.7)",
    neutral: theme === "dark" ? "rgba(156, 163, 175, 0.3)" : "rgba(156, 163, 175, 0.3)",
    text: theme === "dark" ? "text-white" : "text-ink-900"
  };

  const getColor = (value) => {
    const absValue = Math.abs(value);
    if (absValue < 0.3) return colors.neutral;
    return value > 0 ? colors.positive : colors.negative;
  };

  return (
    <div className="mt-4">
      <h4 className={`text-sm font-medium mb-3 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
        Matriz de Correlación de Features
      </h4>
      <div className={`rounded-lg p-4 ${theme === "dark" ? "bg-ink-800" : "bg-ink-50"}`}>
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="p-2"></th>
              {featureNames.map(name => (
                <th key={name} className={`p-2 text-left ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {featureNames.map((rowName, i) => (
              <tr key={rowName}>
                <td className={`p-2 font-medium ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>
                  {rowName}
                </td>
                {featureNames.map((colName, j) => {
                  const value = correlationMatrix[rowName][colName];
                  const bgColor = getColor(value);
                  return (
                    <td 
                      key={colName} 
                      className="p-2 text-center font-tabular"
                      style={{ backgroundColor: bgColor }}
                    >
                      {value.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className={`flex gap-4 mt-3 text-xs ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: colors.positive }}></div>
            <span>Correlación positiva</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: colors.negative }}></div>
            <span>Correlación negativa</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: colors.neutral }}></div>
            <span>Correlación débil</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ROCCurvesChart({ rocCurves, theme }) {
  if (!rocCurves || Object.keys(rocCurves).length === 0) return null;

  const modelColors = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6"
  ];
  
  const chartData = [];
  const maxPoints = 100;
  
  // Convert ROC curves to chart format
  Object.entries(rocCurves).forEach(([modelName, data], index) => {
    const fpr = data.fpr;
    const tpr = data.tpr;
    const step = Math.max(1, Math.floor(fpr.length / maxPoints));
    
    for (let i = 0; i < fpr.length; i += step) {
      chartData.push({
        fpr: fpr[i],
        tpr: tpr[i],
        model: modelName,
        auc: data.auc
      });
    }
  });

  const uniqueModels = [...new Set(chartData.map(d => d.model))];

  return (
    <div className="mt-4">
      <h4 className={`text-sm font-medium mb-3 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
        Curvas ROC Comparativas
      </h4>
      <div className={`rounded-lg p-4 ${theme === "dark" ? "bg-ink-800" : "bg-ink-50"}`}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme === "dark" ? "#374151" : "#e5e7eb"} />
            <XAxis 
              dataKey="fpr" 
              label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5 }}
              stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
            />
            <YAxis 
              label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }}
              stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: theme === "dark" ? "#1f2937" : "#ffffff",
                border: `1px solid ${theme === "dark" ? "#374151" : "#e5e7eb"}`,
                color: theme === "dark" ? "#ffffff" : "#000000"
              }}
            />
            <Legend />
            {uniqueModels.map((modelName, index) => (
              <Line
                key={modelName}
                dataKey="tpr"
                data={chartData.filter(d => d.model === modelName)}
                name={`${modelName} (AUC: ${rocCurves[modelName].auc.toFixed(3)})`}
                stroke={modelColors[index % modelColors.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function FeatureImportanceComparison({ results, theme }) {
  if (!results || results.length === 0) return null;

  const featureNames = Object.keys(results[0].feature_importance);
  const colors = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6"
  ];

  const chartData = featureNames.map(feature => {
    const dataPoint = { feature };
    results.forEach((result, index) => {
      dataPoint[result.model_name] = result.feature_importance[feature] || 0;
    });
    return dataPoint;
  });

  return (
    <div className="mt-4">
      <h4 className={`text-sm font-medium mb-3 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
        Comparación de Feature Importance por Modelo
      </h4>
      <div className={`rounded-lg p-4 ${theme === "dark" ? "bg-ink-800" : "bg-ink-50"}`}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke={theme === "dark" ? "#374151" : "#e5e7eb"} />
            <XAxis 
              type="number"
              label={{ value: 'Importancia (%)', position: 'insideBottom', offset: -5 }}
              stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
            />
            <YAxis 
              type="category"
              dataKey="feature"
              width={120}
              stroke={theme === "dark" ? "#9ca3af" : "#6b7280"}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: theme === "dark" ? "#1f2937" : "#ffffff",
                border: `1px solid ${theme === "dark" ? "#374151" : "#e5e7eb"}`,
                color: theme === "dark" ? "#ffffff" : "#000000"
              }}
            />
            <Legend />
            {results.map((result, index) => (
              <Bar
                key={result.model_name}
                dataKey={result.model_name}
                fill={colors[index % colors.length]}
                name={result.model_name}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function Risk() {
  const { user } = useAuth();
  const [clients, setClients] = useState(null);
  const [trainResult, setTrainResult] = useState(null);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);
  const [showStreamlit, setShowStreamlit] = useState(false);
  const [collectionPriority, setCollectionPriority] = useState(null);
  const [loadingPriority, setLoadingPriority] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);
  const { t } = useTranslation();
  const { theme } = useTheme();

  const canTrain = user?.rol?.toLowerCase() === "administrador" || user?.rol?.toLowerCase() === "contador";

  const loadClients = () => {
    setLoading(true);
    setError("");
    riskService
      .listClients()
      .then((res) => setClients(res.data))
      .catch(() => setError(t("common.unexpectedError")))
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
        setError(t("common.unexpectedError"));
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
        setError(t("common.unexpectedError"));
        setTraining(false);
      });
  };

  const handleCompareModels = () => {
    setComparing(true);
    setError("");
    setCompareResult(null);
    riskService
      .compareModels()
      .then((res) => {
        setCompareResult(res.data);
        setComparing(false);
      })
      .catch(() => {
        setError(t("common.unexpectedError"));
        setComparing(false);
      });
  };

  const handleTrainWithType = (modelType) => {
    setTraining(true);
    setError("");
    setTrainResult(null);
    riskService
      .trainWithType(modelType)
      .then(() => {
        startPolling();
      })
      .catch(() => {
        setError(t("common.unexpectedError"));
        setTraining(false);
      });
  };

  const handleLoadCollectionPriority = () => {
    setLoadingPriority(true);
    setError("");
    invoiceService
      .getCollectionPriority()
      .then((res) => {
        setCollectionPriority(res.data);
        setLoadingPriority(false);
      })
      .catch(() => {
        setError(t("common.unexpectedError"));
        setLoadingPriority(false);
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
    <AppLayout title={t("risk.title")}>
      <div className="flex flex-col gap-6">
        {canTrain && (
          <>
            <Card
              title="Comparación de Modelos"
              action={
                <div className="flex gap-2">
                  <Button onClick={handleCompareModels} disabled={comparing} variant="secondary">
                    {comparing ? (
                      <>
                        <RefreshCw className="animate-spin" size={16} />
                        Comparando...
                      </>
                    ) : (
                      <>
                        <BarChart3 size={16} />
                        Comparar Modelos
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => window.open(import.meta.env.VITE_STREAMLIT_URL || 'http://localhost:8501', '_blank')}
                    variant="primary"
                  >
                    Abrir Streamlit ML
                  </Button>
                </div>
              }
            >
              <p className={`text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
                Compara 5 modelos de machine learning (Logistic Regression, Random Forest, SVM, Gradient Boosting, Neural Network) usando cross-validation de 10-fold.
              </p>

              {compareResult && !comparing && (
                <div className="mt-4 space-y-4">
                  <div className={`p-4 rounded-lg ${theme === "dark" ? "bg-brand-900/20" : "bg-brand-50"}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp size={20} className={theme === "dark" ? "text-brand-400" : "text-brand-600"} />
                      <span className={`font-medium ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                        Mejor Modelo: {compareResult.best_model}
                      </span>
                    </div>
                    <p className={`text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
                      F1-Score: {(compareResult.best_f1 * 100).toFixed(1)}%
                    </p>
                    <p className={`text-sm mt-2 ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                      {compareResult.recommendation}
                    </p>
                    <div className="mt-3">
                      <Button
                        onClick={() => handleTrainWithType("gradient_boosting")}
                        variant="primary"
                        size="sm"
                      >
                        Entrenar Mejor Modelo
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-200"}`}>
                          <th className={`text-left py-2 pr-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Modelo</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>F1</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Accuracy</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Precision</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Recall</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>ROC-AUC</th>
                          <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Tiempo (s)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {compareResult.results.map((result) => (
                          <tr 
                            key={result.model_name} 
                            className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} ${result.model_name === compareResult.best_model ? (theme === "dark" ? "bg-brand-900/10" : "bg-brand-50") : ""} last:border-0`}
                          >
                            <td className={`py-2 pr-2 font-medium ${result.model_name === compareResult.best_model ? (theme === "dark" ? "text-brand-400" : "text-brand-700") : (theme === "dark" ? "text-white" : "text-ink-800")}`}>
                              {result.model_name} {result.model_name === compareResult.best_model && "★"}
                            </td>
                            <td className="py-2 px-2 text-right font-tabular">{(result.f1_mean * 100).toFixed(1)}% ± {(result.f1_std * 100).toFixed(1)}%</td>
                            <td className="py-2 px-2 text-right font-tabular">{(result.accuracy_mean * 100).toFixed(1)}% ± {(result.accuracy_std * 100).toFixed(1)}%</td>
                            <td className="py-2 px-2 text-right font-tabular">{(result.precision_mean * 100).toFixed(1)}% ± {(result.precision_std * 100).toFixed(1)}%</td>
                            <td className="py-2 px-2 text-right font-tabular">{(result.recall_mean * 100).toFixed(1)}% ± {(result.recall_std * 100).toFixed(1)}%</td>
                            <td className="py-2 px-2 text-right font-tabular">{(result.roc_auc_mean * 100).toFixed(1)}% ± {(result.roc_auc_std * 100).toFixed(1)}%</td>
                            <td className="py-2 px-2 text-right font-tabular">{result.training_time.toFixed(2)}s</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {Object.keys(compareResult.statistical_tests).length > 0 && (
                    <div>
                      <h4 className={`text-sm font-medium mb-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>Tests Estadísticos (t-test pareado)</h4>
                      <div className="space-y-1">
                        {Object.entries(compareResult.statistical_tests).map(([test, data]) => (
                          <div key={test} className={`flex items-center justify-between text-xs ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                            <span>{test}:</span>
                            <span className={data.significant ? (theme === "dark" ? "text-green-400" : "text-green-700") : (theme === "dark" ? "text-ink-400" : "text-ink-500")}>
                              p={data.p_value.toFixed(4)} {data.significant ? "(significativo)" : "(no significativo)"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <CorrelationHeatmap correlationMatrix={compareResult.correlation_matrix} theme={theme} />
                  <ROCCurvesChart rocCurves={compareResult.roc_curves} theme={theme} />
                  <FeatureImportanceComparison results={compareResult.results} theme={theme} />
                </div>
              )}
            </Card>

            <Card title={t("risk.uploadDataset")}>
              <div className="flex flex-col gap-4">
                <p className={`text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>{t("risk.uploadInstructions")}</p>
                <div className="flex gap-3 items-center">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.json"
                    onChange={handleFileUpload}
                    className={`block w-full text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-medium
                      file:bg-brand-50 file:text-brand-700
                      hover:file:bg-brand-100`}
                  />
                  <Button
                    onClick={handleUploadDataset}
                    disabled={!uploadFile || training}
                    variant="primary"
                  >
                    <Upload size={16} className="mr-2" />
                    {t("risk.trainWithDataset")}
                  </Button>
                </div>
              </div>
            </Card>

            <Card
              title={t("risk.trainModel")}
              action={
                <Button onClick={handleTrain} disabled={training} variant="primary">
                  {training ? (
                    <>
                      <RefreshCw className="animate-spin" size={16} />
                      {t("risk.training")}
                    </>
                  ) : (
                    <>
                      <BrainCircuit size={16} />
                      {t("risk.trainWithDB")}
                    </>
                  )}
                </Button>
              }
            >
              <p className={`text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
                El modelo se entrena localmente con scikit-learn. No se envía información a servicios externos.
              </p>

              {training && trainingStatus && (
                <div className={`mt-4 p-4 rounded-lg ${theme === "dark" ? "bg-ink-800" : "bg-ink-50"}`}>
                  <ProgressBar progress={trainingStatus.progress} currentStep={trainingStatus.current_step} />
                  {trainingStatus.mensaje && (
                    <p className={`text-sm mt-2 ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>{trainingStatus.mensaje}</p>
                  )}
                </div>
              )}

              {trainResult && !training && (
                <div className={`mt-4 rounded-lg p-4 ${trainResult.entrenado ? (theme === "dark" ? "bg-green-900/20 text-green-400" : "bg-green-50 text-green-800") : (theme === "dark" ? "bg-amber-900/20 text-amber-400" : "bg-amber-50 text-amber-800")}`}>
                  <div className="flex items-start gap-2">
                    {trainResult.entrenado ? (
                      <TrendingUp size={20} className="mt-0.5" />
                    ) : (
                      <AlertCircle size={20} className="mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium">{trainResult.entrenado ? t("risk.trained") : t("risk.notEnoughData")}</p>
                      <p className="text-sm mt-1">{t("risk.samples")}: {trainResult.n_muestras} | {t("risk.highRisk")}: {trainResult.n_clase_alto_riesgo}</p>
                      <p className="text-sm mt-1">Modelo disponible: {trainResult.modelo_disponible ? "Sí" : "No"}</p>
                    </div>
                  </div>
                </div>
              )}

              {trainResult?.eda && (
                <div className="mt-6">
                  <h3 className={`text-sm font-medium mb-3 flex items-center gap-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                    <BarChart3 size={16} />
                    {t("risk.eda")}
                  </h3>
                  <EDACard eda={trainResult.eda} />
                </div>
              )}

              {trainResult?.metrics && (
                <div className="mt-6">
                  <h3 className={`text-sm font-medium mb-3 flex items-center gap-2 ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                    <TrendingUp size={16} />
                    {t("risk.metrics")}
                  </h3>
                  <MetricsCard metrics={trainResult.metrics} />
                </div>
              )}
            </Card>
          </>
        )}

        <Card 
          title="Priorización de Cobranza"
          action={
            <Button onClick={handleLoadCollectionPriority} disabled={loadingPriority} variant="secondary">
              {loadingPriority ? (
                <>
                  <RefreshCw className="animate-spin" size={16} />
                  Cargando...
                </>
              ) : (
                <>
                  <BarChart3 size={16} />
                  Cargar Prioridad
                </>
              )}
            </Button>
          }
        >
          <p className={`text-sm ${theme === "dark" ? "text-ink-300" : "text-ink-600"}`}>
            Lista de clientes priorizados por riesgo de morosidad para gestión de cobranza.
          </p>

          {collectionPriority && !loadingPriority && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"}`}>
                    <th className={`text-left py-2 pr-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Prioridad</th>
                    <th className={`text-left py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Cliente</th>
                    <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Score</th>
                    <th className={`text-center py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Nivel</th>
                    <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>% Vencidas</th>
                    <th className={`text-right py-2 px-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>% Tardíos</th>
                    <th className={`text-right py-2 pl-2 ${theme === "dark" ? "text-ink-400" : "text-ink-700"}`}>Días Mora</th>
                  </tr>
                </thead>
                <tbody>
                  {collectionPriority.map((client, index) => (
                    <tr 
                      key={client.client_id} 
                      className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0 ${index < 3 ? (theme === "dark" ? "bg-red-900/10" : "bg-red-50") : ""}`}
                    >
                      <td className={`py-2 pr-2 font-bold ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                        #{index + 1}
                      </td>
                      <td className={`py-2 px-2 ${theme === "dark" ? "text-ink-300" : "text-ink-700"}`}>
                        {client.cliente_nombre}
                      </td>
                      <td className="py-2 px-2 text-right font-tabular font-medium">
                        {(client.score * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 px-2 text-center">
                        <RiskBadge nivel={client.nivel} />
                      </td>
                      <td className="py-2 px-2 text-right font-tabular">
                        {(client.pct_facturas_vencidas * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-right font-tabular">
                        {(client.pct_pagos_tardios * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 pl-2 text-right font-tabular">
                        {client.dias_mora_promedio.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title={t("risk.title")}>
          {loading && <LoadingState />}
          {error && <ErrorState message={error} />}

          {!loading && !error && clients && (
            <>
              {clients.length === 0 ? (
                <EmptyState title={t("risk.noClients")} description={t("risk.noClientsDesc")} />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} text-left text-xs uppercase tracking-wide ${theme === "dark" ? "text-ink-400" : "text-ink-400"}`}>
                        <th className="py-3 pr-4">{t("risk.client")}</th>
                        <th className="py-3 px-4 text-right">{t("risk.score")}</th>
                        <th className="py-3 px-4">{t("risk.level")}</th>
                        <th className="py-3 px-4">{t("risk.method")}</th>
                        <th className="py-3 px-4 text-right">{t("risk.overdueInvoices")}</th>
                        <th className="py-3 pl-4 text-right">{t("risk.avgOverdueDays")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clients.map((client) => (
                        <tr key={client.client_id} className={`border-b ${theme === "dark" ? "border-ink-800" : "border-ink-100"} last:border-0`}>
                          <td className={`py-3 pr-4 ${theme === "dark" ? "text-white" : "text-ink-800"}`}>{client.cliente_nombre}</td>
                          <td className={`py-3 px-4 text-right font-tabular font-medium ${theme === "dark" ? "text-white" : "text-ink-900"}`}>
                            {(client.score * 100).toFixed(1)}%
                          </td>
                          <td className="py-3 px-4">
                            <RiskBadge nivel={client.nivel} />
                          </td>
                          <td className={`py-3 px-4 capitalize ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                            {client.metodo === "sin_historial" ? t("risk.noHistory") : (client.metodo === "heuristica" ? t("risk.heuristic") : t("risk.model"))}
                          </td>
                          <td className={`py-3 px-4 text-right font-tabular ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
                            {client.factores ? `${(client.factores.pct_facturas_vencidas * 100).toFixed(1)}%` : "-"}
                          </td>
                          <td className={`py-3 pl-4 text-right font-tabular ${theme === "dark" ? "text-ink-400" : "text-ink-600"}`}>
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
