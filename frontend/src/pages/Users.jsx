import { useEffect, useState } from "react";
import { Plus, ShieldCheck } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState } from "../components/ui/States";
import { authService } from "../services/authService";

const ROLE_LABELS = {
  administrador: "Administrador",
  contador: "Contador",
  vendedor: "Vendedor",
};

const USUARIO_VACIO = { nombre: "", email: "", password: "", rol: "vendedor" };

export default function Users() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(USUARIO_VACIO);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = () => {
    setLoading(true);
    authService.listUsers().then((res) => setUsuarios(res.data)).finally(() => setLoading(false));
  };

  useEffect(() => {
    cargar();
  }, []);

  const abrirNuevo = () => {
    setForm(USUARIO_VACIO);
    setError("");
    setModalOpen(true);
  };

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setError("");
    try {
      await authService.createUser(form);
      setModalOpen(false);
      cargar();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "No se pudo crear el usuario");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <AppLayout title="Usuarios">
      <Card>
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-ink-500">Administra las cuentas de acceso al sistema y sus roles.</p>
          <Button onClick={abrirNuevo}>
            <Plus size={16} /> Nuevo usuario
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                <th className="py-2">Nombre</th>
                <th className="py-2">Correo</th>
                <th className="py-2">Rol</th>
                <th className="py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id} className="border-b border-ink-100 last:border-0">
                  <td className="py-2.5 font-medium text-ink-800">{usuario.nombre}</td>
                  <td className="py-2.5 text-ink-600">{usuario.email}</td>
                  <td className="py-2.5">
                    <span className="inline-flex items-center gap-1 rounded-full bg-ink-100 px-2.5 py-1 text-xs font-medium text-ink-700">
                      <ShieldCheck size={12} /> {ROLE_LABELS[usuario.rol]}
                    </span>
                  </td>
                  <td className="py-2.5 text-ink-500">{usuario.activo ? "Activo" : "Inactivo"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo usuario" onClose={() => setModalOpen(false)}>
        <form onSubmit={guardar}>
          <Field label="Nombre completo">
            <Input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
          </Field>
          <Field label="Correo electrónico">
            <Input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>
          <Field label="Contraseña temporal">
            <Input
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>
          <Field label="Rol">
            <Select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
              <option value="vendedor">Vendedor</option>
              <option value="contador">Contador</option>
              <option value="administrador">Administrador</option>
            </Select>
          </Field>

          {error && <p className="mb-3 text-sm text-mora-high">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Creando..." : "Crear usuario"}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
