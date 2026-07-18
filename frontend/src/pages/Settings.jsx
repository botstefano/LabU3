import { useEffect, useState } from "react";
import { Save, CheckCircle2 } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useTranslation } from "react-i18next";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState } from "../components/ui/States";
import { settingsService } from "../services/settingsService";

export default function Settings() {
  const [valores, setValores] = useState(null);
  const [loading, setLoading] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const { t } = useTranslation();
  const { theme } = useTheme();

  useEffect(() => {
    settingsService
      .get()
      .then((res) => setValores(res.data.valores))
      .finally(() => setLoading(false));
  }, []);

  const actualizar = (clave, valor) => setValores({ ...valores, [clave]: valor });

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setGuardado(false);
    try {
      const res = await settingsService.update(valores);
      setValores(res.data.valores);
      setGuardado(true);
      setTimeout(() => setGuardado(false), 2500);
    } finally {
      setGuardando(false);
    }
  };

  if (loading || !valores) {
    return (
      <AppLayout title={t("settings.title")}>
        <LoadingState />
      </AppLayout>
    );
  }

  return (
    <AppLayout title={t("settings.title")}>
      <Card title={t("settings.companyData")} className="mb-6 max-w-2xl">
        <form onSubmit={guardar}>
          <Field label={t("settings.companyName")}>
            <Input
              value={valores.empresa_razon_social}
              onChange={(e) => actualizar("empresa_razon_social", e.target.value)}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("settings.companyRuc")}>
              <Input value={valores.empresa_ruc} onChange={(e) => actualizar("empresa_ruc", e.target.value)} />
            </Field>
            <Field label={t("settings.vatPercentage")}>
              <Input
                type="number"
                step="0.1"
                value={valores.igv_porcentaje}
                onChange={(e) => actualizar("igv_porcentaje", e.target.value)}
              />
            </Field>
          </div>
          <Field label={t("settings.companyAddress")}>
            <Input value={valores.empresa_direccion} onChange={(e) => actualizar("empresa_direccion", e.target.value)} />
          </Field>

          <p className={`mb-2 mt-4 text-sm font-medium ${theme === "dark" ? "text-white" : "text-ink-700"}`}>{t("settings.delinquencyNotifications")}</p>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("settings.autoNotificationsActive")}>
              <Select
                value={valores.notificaciones_morosidad_activas}
                onChange={(e) => actualizar("notificaciones_morosidad_activas", e.target.value)}
              >
                <option value="true">{t("settings.active")}</option>
                <option value="false">{t("settings.inactive")}</option>
              </Select>
            </Field>
            <Field label={t("settings.noticeDaysAdvance")}>
              <Input
                type="number"
                min="1"
                value={valores.dias_aviso_morosidad}
                onChange={(e) => actualizar("dias_aviso_morosidad", e.target.value)}
              />
            </Field>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <Button type="submit" disabled={guardando}>
              <Save size={16} />
              {guardando ? t("settings.saving") : t("settings.save")}
            </Button>
            {guardado && (
              <span className={`flex items-center gap-1 text-sm ${theme === "dark" ? "text-green-400" : "text-brand-700"}`}>
                <CheckCircle2 size={16} />
                {t("settings.saved")}
              </span>
            )}
          </div>
        </form>
      </Card>
    </AppLayout>
  );
}
