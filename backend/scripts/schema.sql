-- =====================================================================
-- Esquema de base de datos: Sistema de Facturacion Electronica
-- con Gestion de Cobranzas. Compatible con PostgreSQL / Supabase.
-- Ejecutar en el editor SQL de Supabase o via psql.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tipos enumerados
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('administrador', 'contador', 'vendedor');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE tipo_documento AS ENUM ('DNI', 'RUC');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_factura AS ENUM ('pendiente', 'pagada', 'vencida', 'anulada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tabla: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol user_role NOT NULL DEFAULT 'vendedor',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- Tabla: clients
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_documento tipo_documento NOT NULL,
    numero_documento VARCHAR(20) NOT NULL UNIQUE,
    nombre_razon_social VARCHAR(200) NOT NULL,
    direccion VARCHAR(255),
    email VARCHAR(150),
    telefono VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_clients_numero_documento ON clients (numero_documento);

-- Tabla: invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serie VARCHAR(4) NOT NULL DEFAULT 'F001',
    numero INTEGER NOT NULL,
    client_id UUID NOT NULL REFERENCES clients (id) ON DELETE RESTRICT,
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    igv NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    estado estado_factura NOT NULL DEFAULT 'pendiente',
    created_by UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (serie, numero)
);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices (client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_estado ON invoices (estado);
CREATE INDEX IF NOT EXISTS idx_invoices_fecha_emision ON invoices (fecha_emision);

-- Tabla: invoice_items
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices (id) ON DELETE CASCADE,
    descripcion VARCHAR(255) NOT NULL,
    cantidad NUMERIC(10, 2) NOT NULL DEFAULT 1,
    precio_unitario NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items (invoice_id);

-- Tabla: payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices (id) ON DELETE CASCADE,
    fecha_pago DATE NOT NULL DEFAULT CURRENT_DATE,
    monto NUMERIC(12, 2) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL DEFAULT 'transferencia',
    registrado_por UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments (invoice_id);

-- Tabla: app_settings (panel de configuracion clave-valor)
CREATE TABLE IF NOT EXISTS app_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clave VARCHAR(100) NOT NULL UNIQUE,
    valor VARCHAR(1000) NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
