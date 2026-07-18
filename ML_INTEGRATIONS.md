# Integraciones Automáticas de Machine Learning

## Visión General

El sistema ahora integra el modelo de Machine Learning de forma automática en el flujo de negocio, proporcionando alertas y recomendaciones en tiempo real para la toma de decisiones.

## Funcionalidades Implementadas

### 1. Alertas de Riesgo al Crear Facturas

**Propósito:** Advertir al usuario cuando crea una factura para un cliente con alto riesgo de morosidad.

**Flujo:**
```
Usuario crea factura → Sistema calcula riesgo del cliente → 
Si riesgo > 70%: Muestra alerta con factores → Usuario decide continuar o editar
```

**Implementación Backend:**
- `InvoiceService.create()`: Calcula riesgo automáticamente después de crear la factura
- Retorna tupla: `(Invoice, Optional[dict])` con alerta de riesgo si aplica
- Umbral: score > 0.7 (70%)

**Implementación Frontend:**
- `Invoices.jsx`: Muestra alerta visual en modal de creación
- Botones: "Editar factura" o "Confirmar de todas formas"
- Información mostrada: nivel, score, factores (vencidas, tardíos, días mora)

**Endpoint API:**
- `POST /api/invoices` → Retorna `InvoiceCreateResponse` con `risk_alert`

**Schema:**
```python
class RiskAlert(BaseModel):
    nivel: str
    score: float
    mensaje: str
    factores: dict

class InvoiceCreateResponse(BaseModel):
    invoice: InvoiceResponse
    risk_alert: Optional[RiskAlert] = None
```

**Uso Práctico:**
- Vendedor crea factura → Sistema advierte riesgo alto → Vendedor puede:
  - Solicitar pago anticipado
  - Reducir monto de la factura
  - Solicitar garantías adicionales
  - Decidir no emitir factura

### 2. Priorización de Cobranza

**Propósito:** Ordenar clientes por riesgo de morosidad para optimizar esfuerzos de cobranza.

**Flujo:**
```
Usuario solicita lista de cobranza → Sistema calcula riesgo de todos los clientes → 
Ordena por riesgo (mayor primero) → Muestra lista priorizada
```

**Implementación Backend:**
- `RiskService.listar_clientes_para_cobranza()`: Calcula riesgo de todos los clientes
- Actualiza estados de facturas vencidas primero
- Ordena por score descendente (mayor riesgo primero)
- Retorna lista con: cliente, score, nivel, factores

**Implementación Frontend:**
- `Risk.jsx`: Card "Priorización de Cobranza"
- Botón "Cargar Prioridad"
- Tabla con: prioridad (#), cliente, score, nivel, factores
- Resaltado visual para top 3 (rojo claro)

**Endpoint API:**
- `GET /api/risk/collection-priority` → Retorna lista priorizada

**Uso Práctico:**
- Equipo de cobranza ve lista priorizada → Enfoca esfuerzos en clientes de alto riesgo
- Top 3 clientes priorizados (resaltados en rojo)
- Permite seguimiento sistemático de clientes problemáticos

### 3. Sugerencia de Límites de Crédito

**Propósito:** Recomendar límites de crédito basados en el riesgo del cliente.

**Flujo:**
```
Usuario solicita límite de crédito → Sistema calcula riesgo del cliente → 
Retorna límite sugerido basado en nivel de riesgo → Usuario ve justificación
```

**Implementación Backend:**
- `RiskService.sugerir_limite_credito(client_id)`: Calcula riesgo del cliente
- Retorna límite según nivel:
  - Riesgo bajo: S/ 10,000
  - Riesgo medio: S/ 5,000
  - Riesgo alto: S/ 1,000
- Incluye justificación y factores

**Implementación Frontend:**
- `Clients.jsx`: Botón de ícono de tendencia en tabla de clientes
- Modal con: límite sugerido, nivel de riesgo, justificación, factores
- Botón "Cerrar" para aceptar sugerencia

**Endpoint API:**
- `GET /api/risk/credit-limit/{client_id}` → Retorna sugerencia de límite

**Uso Práctico:**
- Gerente de crédito evalúa nuevo cliente → Solicita límite sugerido → 
- Sistema recomienda S/ 5,000 (riesgo medio) → Gerente ajusta según criterios adicionales

## Arquitectura de Integración

### Flujo de Datos

```
Base de Datos (PostgreSQL)
    ↓
RiskService.score_client()
    ↓
Modelo ML (risk_model.joblib) o Heurística
    ↓
Cálculo de riesgo (score 0-1, nivel bajo/medio/alto)
    ↓
Integración en flujo de negocio
    ├── Alertas en creación de facturas
    ├── Priorización de cobranza
    └── Sugerencias de límites de crédito
```

### Componentes Involucrados

**Backend:**
- `InvoiceService`: Integración de alertas de riesgo
- `RiskService`: Cálculo de riesgo y priorización
- `risk_router.py`: Endpoints para cobranza y límites
- `invoice_router.py`: Endpoint de creación con alertas
- `risk_model.py`: Modelo ML y heurística

**Frontend:**
- `Invoices.jsx`: Alertas de riesgo en creación
- `Risk.jsx`: Priorización de cobranza
- `Clients.jsx`: Sugerencias de límites de crédito
- `invoiceService.js`: Llamadas a API

## Casos de Uso

### Caso 1: Vendedor Crea Factura

**Situación:** Vendedor crea factura de S/ 8,000 para cliente habitual.

**Flujo:**
1. Vendedor selecciona cliente y completa factura
2. Al guardar, sistema calcula riesgo automáticamente
3. Si riesgo > 70%, muestra alerta:
   - "⚠️ Cliente con alto riesgo de morosidad (78%)"
   - Factores: % vencidas, % tardíos, días mora
4. Vendedor puede:
   - Editar factura (reducir monto)
   - Confirmar de todas formas
5. Si confirma, factura se guarda normalmente

**Beneficio:** Vendedor toma decisión informada en tiempo real.

### Caso 2: Equipo de Cobranza

**Situación:** Equipo de cobranza necesita priorizar esfuerzos finitos.

**Flujo:**
1. Navega a página de Riesgo
2. Hace clic en "Cargar Prioridad"
3. Sistema muestra lista ordenada:
   - #1: Cliente A (85% riesgo, alto)
   - #2: Cliente B (72% riesgo, alto)
   - #3: Cliente C (65% riesgo, medio)
   - #4: Cliente D (30% riesgo, bajo)
4. Equipo enfoca esfuerzos en top 3

**Beneficio:** Optimización de recursos de cobranza.

### Caso 3: Gerente de Crédito

**Situación:** Nuevo cliente solicita línea de crédito.

**Flujo:**
1. Gerente ve perfil del cliente en lista de clientes
2. Hace clic en botón de tendencia (límite crédito)
3. Sistema muestra modal:
   - Límite sugerido: S/ 5,000
   - Nivel de riesgo: MEDIO
   - Score: 45%
   - Justificación: "Cliente con riesgo medio de morosidad. Límite de crédito moderado."
   - Factores: % vencidas, % tardíos, días mora
4. Gerente ajusta según criterios adicionales (referencias, garantías)

**Beneficio:** Decisión de crédito basada en datos históricos.

## Métricas y KPIs

### Métricas de Impacto

**Para el artículo:**
- **Tasa de adopción:** % de usuarios que siguen recomendaciones
- **Reducción de morosidad:** % de reducción en facturas vencidas
- **Eficiencia de cobranza:** Tiempo promedio de recuperación
- **Precisión del modelo:** % de predicciones correctas

**Para producción:**
- **Alertas aceptadas:** % de facturas modificadas tras alerta
- **Cobranza priorizada:** % de recuperación de top 3 clientes
- **Límites ajustados:** % de límites cercanos a sugerencia

## Configuración

### Umbrales Configurables

**En `InvoiceService.create()`:**
```python
if riesgo.score > 0.7:  # Umbral de alerta
    riesgo_alerta = {...}
```

**En `RiskService.sugerir_limite_credito()`:**
```python
if riesgo.nivel == "bajo":
    limite = 10000  # S/ 10,000
elif riesgo.nivel == "medio":
    limite = 5000   # S/ 5,000
else:  # alto
    limite = 1000   # S/ 1,000
```

### Personalización

Los umbrales y límites pueden ajustarse según:
- Política de riesgo de la empresa
- Tolerancia al riesgo
- Condiciones del mercado
- Historial del cliente

## Limitaciones y Consideraciones

### Limitaciones Actuales

1. **Cálculo On-Demand:** Riesgo se calcula cuando se solicita, no en tiempo real
2. **Modelo Estático:** Modelo no se reentrena automáticamente
3. **Heurística Fallback:** Si no hay modelo entrenado, usa heurística simple
4. **Sin Contexto Temporal:** No considera tendencias temporales

### Mejoras Futuras

1. **Job Programado:** Recalcular riesgo automáticamente cada noche
2. **Reentrenamiento Automático:** Retrain modelo periódicamente
3. **Alertas Proactivas:** Notificar cuando riesgo de cliente cambia
4. **Modelos Ensemble:** Combinar múltiples modelos para mayor precisión
5. **Features Temporales:** Incluir tendencias y patrones temporales

## Seguridad y Autorización

### Roles Requeridos

**Alertas de riesgo:**
- Todos los roles (ADMINISTRADOR, VENDEDOR, CONTADOR)

**Priorización de cobranza:**
- Todos los roles autenticados

**Sugerencia de límites de crédito:**
- Todos los roles autenticados

**Entrenamiento de modelos:**
- Solo ADMINISTRADOR y CONTADOR

### Auditoría

Todas las integraciones registran:
- Usuario que realizó la acción
- Timestamp de la acción
- Resultado del cálculo de riesgo
- Decisión tomada (aceptar/rechazar sugerencia)

## Monitoreo y Logging

### Logs Importantes

```python
# En InvoiceService.create()
logger.info(f"Riesgo calculado para cliente {client_id}: {riesgo.score}")

# En RiskService.listar_clientes_para_cobranza()
logger.info(f"Priorización de cobranza: {len(clientes)} clientes ordenados")

# En RiskService.sugerir_limite_credito()
logger.info(f"Límite sugerido para cliente {client_id}: {limite}")
```

### Métricas a Monitorear

- Tiempo de respuesta de cálculo de riesgo
- Tasa de errores en cálculo de riesgo
- Frecuencia de uso de cada integración
- Tasa de aceptación de sugerencias

## Testing

### Pruebas Unitarias

```python
def test_alerta_riesgo_alta():
    # Crear factura con cliente de alto riesgo
    invoice, alerta = service.create(data, user_id)
    assert alerta is not None
    assert alerta["score"] > 0.7

def test_priorizacion_cobranza():
    # Obtener lista priorizada
    lista = service.listar_clientes_para_cobranza()
    assert len(lista) > 0
    assert lista[0]["score"] >= lista[1]["score"]

def test_sugerencia_limite():
    # Obtener sugerencia de límite
    sugerencia = service.sugerir_limite_credito(client_id)
    assert sugerencia["limite_sugerido"] > 0
    assert sugerencia["nivel_riesgo"] in ["bajo", "medio", "alto"]
```

### Pruebas de Integración

- Crear factura con cliente de alto riesgo → Verificar alerta
- Cargar lista priorizada → Verificar orden correcto
- Solicitar límite de crédito → Verificar sugerencia razonable

## Conclusión

Las integraciones automáticas de ML transforman el sistema de facturación de una herramienta pasiva a un asistente activo que:

- **Advierte riesgos** en tiempo real
- **Prioriza esfuerzos** de cobranza
- **Recomienda decisiones** de crédito

Esto demuestra el valor práctico del ML en el flujo de negocio y proporciona casos de uso medibles para el artículo académico.
