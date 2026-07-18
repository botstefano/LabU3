# Arquitectura Híbrida React + Streamlit

## Visión General

El proyecto utiliza una arquitectura híbrida que combina:
- **Frontend React**: Aplicación principal de facturación
- **Backend FastAPI**: API REST para operaciones de negocio
- **Servicio Streamlit**: Visualizaciones avanzadas de Machine Learning

## Diagrama de Arquitectura

```
┌─────────────────┐
│  Frontend React │
│  (Vite + React) │
└────────┬────────┘
         │
         ├──► FastAPI Backend (API REST)
         │    ├── Clientes, Facturas, Pagos
         │    ├── Autenticación JWT
         │    └── Lógica de negocio
         │
         └──► Streamlit ML (Nueva ventana)
              ├── Comparación de 5 modelos
              ├── Visualizaciones interactivas
              ├── Análisis estadístico
              └── Screenshots para artículo
```

## Servicios

### 1. Frontend React
**Propósito:** Aplicación principal de facturación electrónica

**Tecnologías:**
- React 18 + Vite
- Tailwind CSS
- React Router
- Axios
- Recharts (visualizaciones básicas)

**Funcionalidades:**
- Gestión de clientes
- Creación de facturas
- Pagos y cobranzas
- Reportes PDF
- Integración con ML (botón para abrir Streamlit)

**Acceso:** http://localhost:5173 (desarrollo) / URL de Render (producción)

### 2. Backend FastAPI
**Propósito:** API REST para operaciones de negocio

**Tecnologías:**
- FastAPI
- SQLAlchemy ORM
- PostgreSQL (Supabase)
- JWT Authentication
- Scikit-learn (ML básico)

**Funcionalidades:**
- CRUD de clientes, facturas, pagos
- Autenticación y autorización
- Generación de PDFs
- Exportación Excel
- Endpoints ML (comparación de modelos)

**Acceso:** http://localhost:8000 (desarrollo) / URL de Render (producción)

### 3. Servicio Streamlit (Nuevo)
**Propósito:** Visualizaciones avanzadas de Machine Learning

**Tecnologías:**
- Streamlit
- Plotly (gráficos interactivos)
- Pandas (manipulación de datos)
- Scikit-learn (modelos ML)

**Funcionalidades:**
- Comparación de 5 modelos ML
- Cross-validation 10-fold
- Pruebas estadísticas (t-test)
- Matriz de correlación (heatmap)
- Curvas ROC comparativas
- Feature importance comparativo
- Exportación de visualizaciones

**Acceso:** http://localhost:8501 (desarrollo) / URL de Render (producción)

## Flujo de Trabajo para el Artículo

### 1. Desarrollo Local

**Iniciar servicios:**
```bash
# Terminal 1: Backend FastAPI
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend React
cd frontend
npm run dev

# Terminal 3: Streamlit ML
cd backend
streamlit run streamlit_app.py
```

**Generar datos de demo:**
```bash
cd backend
python scripts/seed_demo_data.py
```

**Flujo para el artículo:**
1. Usar React para gestión de facturación normal
2. Hacer clic en "Abrir Streamlit ML" en la página de Riesgo
3. En Streamlit: hacer clic en "Comparar 5 Modelos"
4. Visualizar resultados con gráficos interactivos
5. Capturar screenshots para el artículo

### 2. Producción (Render)

**Servicios desplegados:**
- `facturacion-backend`: FastAPI (Docker)
- `facturacion-frontend`: React (Static)
- `facturacion-ml`: Streamlit (Python)

**Configuración:**
- Todos los servicios comparten la misma base de datos PostgreSQL
- Variables de ambiente sincronizadas
- CORS configurado para comunicación entre servicios

## Integración React-Streamlit

### Método: Nueva Ventana

**Implementación actual:**
```javascript
// En Risk.jsx
<Button 
  onClick={() => window.open('http://localhost:8501', '_blank')} 
  variant="primary"
>
  Abrir Streamlit ML
</Button>
```

**Ventajas:**
- Simple de implementar
- Streamlit tiene su propio contexto
- Screenshots fáciles de capturar
- No interfiere con React

**Desventajas:**
- Usuario debe cambiar de ventana
- No integración visual directa

### Alternativa: Iframe (Futuro)

```javascript
<iframe 
  src="http://localhost:8501" 
  width="100%" 
  height="800px"
  style={{ border: 'none' }}
/>
```

**Requiere:**
- Configurar CORS en Streamlit
- Ajustar altura dinámicamente
- Manejar autenticación

## Ventajas de la Arquitectura Híbrida

### 1. Especialización
- **React**: UI compleja y dinámica
- **Streamlit**: Visualizaciones ML especializadas
- **FastAPI**: API robusta y escalable

### 2. Desarrollo Rápido
- Prototipado ML en Streamlit es más rápido
- React para UI de negocio ya está establecido
- No recompilar todo el frontend para cambios ML

### 3. Para el Artículo
- **Screenshots profesionales**: Streamlit genera gráficos de alta calidad
- **Interactividad**: Explorar datos antes de escribir el artículo
- **Reproducibilidad**: Código Streamlit fácil de compartir

### 4. Costo
- **Render Free Tier**: 3 servicios gratuitos
- **Backend**: Docker (free tier)
- **Frontend**: Static (free tier)
- **ML**: Python (free tier)

## Comparación con Arquitecturas Alternativas

### Arquitectura 1: Todo en React (Anterior)
- ✅ Un solo servicio
- ✅ UI consistente
- ❌ Visualizaciones ML más complejas
- ❌ Más código React

### Arquitectura 2: Todo en Streamlit
- ✅ Visualizaciones ML nativas
- ✅ Menos código
- ❌ UI de negocio menos flexible
- ❌ No es ideal para aplicaciones complejas

### Arquitectura 3: Híbrida (Actual) ⭐
- ✅ Mejor de ambos mundos
- ✅ Especialización de tecnologías
- ✅ Desarrollo más rápido
- ❌ Más servicios a mantener
- ❌ Comunicación entre servicios

## Deployment en Render

### Configuración en render.yaml

```yaml
services:
  - type: web
    name: facturacion-backend
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    
  - type: web
    name: facturacion-frontend
    runtime: static
    buildCommand: cd frontend && npm install && npm run build
    
  - type: web
    name: facturacion-ml
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run streamlit_app.py --server.port=$PORT
```

### Variables de Ambiente

Compartidas entre servicios:
- `DATABASE_URL`: Conexión a PostgreSQL
- `ENVIRONMENT`: production/development

Específicas:
- Frontend: `VITE_API_URL`
- Backend: `JWT_SECRET_KEY`, `CORS_ORIGINS`
- ML: Hereda DATABASE_URL del backend

## Desarrollo Local

### Requisitos Previos

```bash
# Python 3.9+
pip install -r backend/requirements.txt

# Node.js 18+
cd frontend
npm install
```

### Iniciar Servicios

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend  
cd frontend
npm run dev

# Terminal 3: Streamlit
cd backend
streamlit run streamlit_app.py
```

### Acceso Local

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Streamlit ML: http://localhost:8501
- Base de datos: PostgreSQL local o Supabase

## Troubleshooting

### Streamlit no conecta a la base de datos

**Problema:** Error de conexión a PostgreSQL

**Solución:**
```bash
# Verificar DATABASE_URL en .env
echo $DATABASE_URL

# Asegurar que PostgreSQL esté corriendo
# O usar Supabase en la nube
```

### CORS entre servicios

**Problema:** React no puede conectar con FastAPI

**Solución:**
```python
# En backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Streamlit lento

**Problema:** Visualizaciones tardan en cargar

**Solución:**
```python
# Usar @st.cache_resource para conexiones a DB
@st.cache_resource
def get_db_engine():
    return create_engine(DATABASE_URL)
```

## Futuras Mejoras

### 1. Integración más profunda
- Iframe embebido en React
- Compartición de estado entre servicios
- Autenticación unificada

### 2. Optimización
- Caching de resultados ML
- WebSockets para comunicación en tiempo real
- CDN para assets estáticos

### 3. Monitoreo
- Logs centralizados
- Métricas de rendimiento
- Alertas de errores

## Conclusión

La arquitectura híbrida React + Streamlit proporciona:
- **Flexibilidad**: Cada tecnología en su área de especialización
- **Velocidad**: Desarrollo más rápido con herramientas apropiadas
- **Calidad**: Visualizaciones profesionales para el artículo
- **Escalabilidad**: Servicios independientes que pueden escalar

Para el artículo académico, esta arquitectura es ideal porque combina la robustez de React para la aplicación de negocio con la facilidad de Streamlit para análisis y visualizaciones ML.
