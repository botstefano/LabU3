import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import AppLayout from "../components/layout/AppLayout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import { Field, Input, Select } from "../components/ui/FormElements";
import { LoadingState, EmptyState } from "../components/ui/States";
import { clientService } from "../services/clientService";

const CLIENTE_VACIO = {
  tipo_documento: "DNI",
  numero_documento: "",
  nombre_razon_social: "",
  direccion: "",
  email: "",
  telefono: "",
};

export default function Clients() {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(CLIENTE_VACIO);
  const [errores, setErrores] = useState({});
  const [guardando, setGuardando] = useState(false);

  const cargar = async (busqueda = "") => {
    setLoading(true);
    try {
      const res = await clientService.list({ search: busqueda || undefined });
      setClientes(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const handleSearch = (event) => {
    event.preventDefault();
    cargar(search);
  };

  const abrirNuevo = () => {
    setEditando(null);
    setForm(CLIENTE_VACIO);
    setErrores({});
    setModalOpen(true);
  };

  const abrirEditar = (cliente) => {
    setEditando(cliente);
    setForm({
      tipo_documento: cliente.tipo_documento,
      numero_documento: cliente.numero_documento,
      nombre_razon_social: cliente.nombre_razon_social,
      direccion: cliente.direccion || "",
      email: cliente.email || "",
      telefono: cliente.telefono || "",
    });
    setErrores({});
    setModalOpen(true);
  };

  const guardar = async (event) => {
    event.preventDefault();
    setGuardando(true);
    setErrores({});
    try {
      if (editando) {
        await clientService.update(editando.id, form);
      } else {
        await clientService.create(form);
      }
      setModalOpen(false);
      cargar(search);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setErrores({ general: typeof detail === "string" ? detail : "No se pudo guardar el cliente" });
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (cliente) => {
    if (!confirm(`¿Eliminar al cliente ${cliente.nombre_razon_social}?`)) return;
    await clientService.remove(cliente.id);
    cargar(search);
  };

  return (
    <AppLayout title="Clientes">
      <Card>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <form onSubmit={handleSearch} className="flex w-full max-w-sm items-center gap-2">
            <Input
              placeholder="Buscar por nombre o documento..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button type="submit" variant="secondary">
              <Search size={16} />
            </Button>
          </form>
          <Button onClick={abrirNuevo}>
            <Plus size={16} /> Nuevo cliente
          </Button>
        </div>

        {loading && <LoadingState />}
        {!loading && clientes.length === 0 && (
          <EmptyState title="No hay clientes registrados" description="Registra tu primer cliente para comenzar a emitir facturas." />
        )}

        {!loading && clientes.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-400">
                <th className="py-2">Cliente</th>
                <th className="py-2">Documento</th>
                <th className="py-2">Contacto</th>
                <th className="py-2 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente) => (
                <tr key={cliente.id} className="border-b border-ink-100 last:border-0">
                  <td className="py-2.5 font-medium text-ink-800">{cliente.nombre_razon_social}</td>
                  <td className="py-2.5 text-ink-600">
                    {cliente.tipo_documento} {cliente.numero_documento}
                  </td>
                  <td className="py-2.5 text-ink-500">{cliente.email || cliente.telefono || "—"}</td>
                  <td className="py-2.5 text-right">
                    <button onClick={() => abrirEditar(cliente)} className="mr-2 text-ink-400 hover:text-brand-600">
                      <Pencil size={16} />
                    </button>
                    <button onClick={() => eliminar(cliente)} className="text-ink-400 hover:text-mora-high">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={modalOpen} title={editando ? "Editar cliente" : "Nuevo cliente"} onClose={() => setModalOpen(false)}>
        <form onSubmit={guardar}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo de documento">
              <Select
                value={form.tipo_documento}
                onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })}
              >
                <option value="DNI">DNI</option>
                <option value="RUC">RUC</option>
              </Select>
            </Field>
            <Field label="Número de documento">
              <Input
                required
                value={form.numero_documento}
                onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
              />
            </Field>
          </div>
          <Field label="Nombre o razón social">
            <Input
              required
              value={form.nombre_razon_social}
              onChange={(e) => setForm({ ...form, nombre_razon_social: e.target.value })}
            />
          </Field>
          <Field label="Dirección">
            <Input value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Correo electrónico">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Teléfono">
              <Input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
            </Field>
          </div>

          {errores.general && <p className="mb-3 text-sm text-mora-high">{errores.general}</p>}

          <div className="mt-2 flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
