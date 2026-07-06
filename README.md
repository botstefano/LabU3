# Sistema de Facturación Electrónica con Gestión de Cobranzas

Backend en FastAPI + PostgreSQL (Supabase) y frontend en React (Vite) + Tailwind CSS.

## Estructura

```
backend/    API REST (FastAPI, SQLAlchemy, JWT, PDF/Excel)
frontend/   SPA en React + Tailwind
render.yaml Configuración de despliegue en Render (backend + frontend)
```

## 1. Base de datos (Supabase)

1. Crea un proyecto en https://supabase.com.
2. En el editor SQL de Supabase, ejecuta el contenido de `backend/scripts/schema.sql`.
3. Copia la cadena de conexión (Project Settings → Database → Connection string → URI).

## 2. Backend (local)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # completa DATABASE_URL con la cadena de Supabase
uvicorn app.main:app --reload
```

- Documentación interactiva: http://localhost:8000/docs
- Crear el primer usuario administrador:
  ```bash
  python scripts/seed_admin.py
  ```
- Ejecutar pruebas automatizadas (usan SQLite en memoria, no requieren Supabase):
  ```bash
  pytest
  ```

## 3. Frontend (local)

```bash
cd frontend
npm install
cp .env.example .env   # define VITE_API_URL=http://localhost:8000
npm run dev
```

## 4. Despliegue en Render

Con el repositorio subido a GitHub, en Render usa "New → Blueprint" y selecciona este repositorio; Render detectará `render.yaml` y creará dos servicios:

- **facturacion-backend**: API FastAPI (Docker). Configura la variable `DATABASE_URL` con la cadena de Supabase y `CORS_ORIGINS` con la URL del frontend desplegado.
- **facturacion-frontend**: sitio estático generado con Vite. Configura `VITE_API_URL` con la URL pública del backend.

Alternativamente, cada servicio puede crearse manualmente desde la consola de Render apuntando a las carpetas `backend/` y `frontend/` respectivamente.

## 5. Subir a un repositorio Git

```bash
git init
git add .
git commit -m "Sistema de facturacion electronica con gestion de cobranzas"
git branch -M main
git remote add origin <URL_DE_TU_REPOSITORIO>
git push -u origin main
```

## Roles del sistema

| Rol | Permisos |
|---|---|
| administrador | Acceso total: usuarios, configuración, clientes, facturas, cobranzas, reportes |
| contador | Facturas, cobranzas (registro de pagos y anulación), reportes, clientes |
| vendedor | Clientes, emisión de facturas, reportes |
