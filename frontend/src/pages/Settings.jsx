import { useEffect, useState } from "react";
import { Save, CheckCircle2 } from "lucide-react";
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
      <AppLayout title="Configuración">
        <LoadingState />
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Configuración">
      <Card title="Datos de la empresa emisora" className="mb-6 max-w-2xl">
        <form onSubmit={guardar}>
          <Field label="Razón social">
            <Input
              value={valores.empresa_razon_social}
              onChange={(e) => actualizar("empresa_razon_social", e.target.value)}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="RUC">
              <Input value={valores.empresa_ruc} onChange={(e) => actualizar("empresa_ruc", e.target.value)} />
            </Field>
            <Field label="Porcentaje de IGV (%)">
              <Input
                type="number"
                step="0.1"
                value={valores.igv_porcentaje}
                onChange={(e) => actualizar("igv_porcentaje", e.target.value)}
              />
            </Field>
          </div>
          <Field label="Dirección">
            <Input value={valores.empresa_direccion} onChange={(e) => actualizar("empresa_direccion", e.target.value)} />
          </Field>

          <p className="mb-2 mt-4 text-sm font-medium text-ink-700">Notificaciones de morosidad</p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Notificaciones automáticas activas">
              <Select
                value={valores.notificaciones_morosidad_activas}
                onChange={(e) => actualizar("notificaciones_morosidad_activas", e.target.value)}
              >
                <option value="true">Activas</option>
                <option value="false">Desactivadas</option>
              </Select>
            </Field>
            <Field label="Días de anticipación de aviso">
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
              <Save size={16} /> {guardando ? "Guardando..." : "Guardar cambios"}
            </Button>
            {guardado && (
              <span className="flex items-center gap-1 text-sm text-brand-700">
                <CheckCircle2 size={16} /> Configuración actualizada
              </span>
            )}
          </div>
        </form>
      </Card>
    </AppLayout>
  );
}
