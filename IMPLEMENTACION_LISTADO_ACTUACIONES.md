# 📋 IMPLEMENTACIÓN: LISTADO DE ACTUACIONES CON FILTROS

## 🎯 Objetivo
Implementar un sistema de listado de actuaciones con filtros avanzados (fecha, tipo, contraproducencia, orden de trabajo) siguiendo la arquitectura modular por dominios.

---

## ✅ BACKEND IMPLEMENTADO

### 1. Schema de Validación Pydantic
**Archivo:** `Backend/app/domains/actuaciones/schemas/list_filters.py`

**Funcionalidades:**
- ✅ Validación de filtros (`desde`, `hasta`, `tipo`, `contraproducencia`, `orden_trabajo`, `page`, `page_size`)
- ✅ **Defaults inteligentes:**
  - Si `desde` y `hasta` vacíos → mes corriente
  - Si solo `desde` → hasta = hoy
  - Si solo `hasta` → desde = primer día del mes de `hasta`
- ✅ Validación: `desde <= hasta`
- ✅ Validación de enums (`tipo`, `contraproducencia`)
- ✅ Paginación (page >= 1, page_size entre 1-500)

**Clase principal:**
```python
class ActuacionesListFilters(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    tipo: Optional[str] = None
    contraproducencia: Optional[str] = None
    orden_trabajo: Optional[str] = None
    page: int = 1
    page_size: int = 50
```

---

### 2. Service de Listado
**Archivo:** `Backend/app/domains/actuaciones/services/list_service.py`

**Función:** `listar_actuaciones_con_filtros(filters: ActuacionesListFilters)`

**Funcionalidades:**
- ✅ Aplica filtros SQLAlchemy (fecha, tipo, contraproducencia)
- ✅ Búsqueda de orden de trabajo (exacta)
- ✅ **Raise `ValueError`** si orden_trabajo no existe
- ✅ Cuenta total antes de paginar
- ✅ Ordenamiento: `id DESC`
- ✅ Paginación con offset/limit

**Retorna:**
```python
{
    "items": [...],  # lista de Actuaciones (modelo DB)
    "meta": {
        "total": 123,
        "page": 1,
        "page_size": 50,
        "desde": "2025-01-01",
        "hasta": "2025-01-31",
        "tipo": "INSPECCION",
        "contraproducencia": "LOCAL CERRADO",
        "orden_trabajo": None
    }
}
```

---

### 3. Presenter para List Item
**Archivo:** `Backend/app/domains/actuaciones/presenters/list_item.py`

**Función:** `actuacion_to_list_item(act: Actuaciones)`

**Funcionalidades:**
- ✅ Convierte modelo DB a DTO simplificado
- ✅ Incluye solo campos relevantes para tabla
- ✅ Aplana relaciones (domicilio, rubro, inspectores, actas)

**Retorna:**
```python
{
    "id": 1,
    "fecha_actuacion": "2025-01-14",
    "tipo_actuacion": "INSPECCION",
    "contraproducencia": "NO_HUBO",
    "orden_trabajo_numero": "123",
    "inspector1": "PEREZ",
    "calle": "AV CORDOBA",
    "numero": "1234",
    "rubro_nombre": "CARNICERIA",
    "acta_inspeccion_num": "456",
    "acta_notificacion_num": "789",
    "acta_comprobacion_num": "012"
}
```

---

### 4. Route Refactorizada
**Archivo:** `Backend/app/domains/actuaciones/routes/list.py`

**Endpoint:** `GET /actuaciones`

**Query Params:**
- `desde` (YYYY-MM-DD, opcional)
- `hasta` (YYYY-MM-DD, opcional)
- `tipo` (opcional: INSPECCION|REINSPECCION|RATIFICACION DE CLAUSURA|RATIFICACION DE DECOMISO|VERIFICAR E INFORMAR|TRANSPORTE)
- `contraproducencia` (opcional: LOCAL CERRADO|NO EXISTE/NO ES EL RUBRO|CLIMA|ZONA ROJA|NO_HUBO|OTROS)
- `orden_trabajo` (opcional: número exacto)
- `page` (default: 1)
- `page_size` (default: 50)

**Respuestas:**
- `200`: Lista con items y metadata
- `400`: Orden de trabajo no encontrada
- `422`: Error de validación Pydantic
- `500`: Error interno

**Ejemplo:**
```bash
GET /actuaciones?desde=2025-01-01&hasta=2025-01-31&tipo=INSPECCION&page=1
```

---

## 🎨 FRONTEND: ESTRUCTURA CREADA

### 1. API Client
**Archivo:** `Frontend/src/api/actuacionesListApi.ts`

**Funcionalidades:**
- ✅ Tipos TypeScript (`IActuacionListItem`, `IActuacionesListResponse`, `IActuacionesListFilters`)
- ✅ Función `getActuacionesFiltered(filters?)`
- ✅ Construye query params dinámicamente

---

### 2. Hook Personalizado
**Archivo:** `Frontend/src/Containers/Actuaciones/hooks/useActuacionesFiltradas.ts`

**Hook:** `useActuacionesFiltradas(filters)`

**Retorna:**
```typescript
{
    actuaciones: IActuacionListItem[];
    meta: IActuacionesListMeta | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}
```

**Funcionalidades:**
- ✅ Encapsula lógica de fetching
- ✅ Manejo de loading/error
- ✅ Auto-refetch cuando cambian filtros
- ✅ Función `refetch` manual

---

### 3. Componente de Filtro
**Archivo:** `Frontend/src/Containers/Actuaciones/Components/FiltroFechas.tsx`

**Props:**
```typescript
interface FiltroFechasProps {
    onFiltrar: (filtros: { ... }) => void;
}
```

**Funcionalidades:**
- ✅ DatePickers para desde/hasta
- ✅ Dropdowns para tipo y contraproducencia
- ✅ Input para orden de trabajo
- ✅ Botones "Filtrar" y "Limpiar"
- ⚠️ **TODO:** Implementar estilos Neo-Brutalistas

---

### 4. Estilos (Placeholder)
**Archivo:** `Frontend/src/Containers/Actuaciones/styles/filtroStyles.ts`

- ⚠️ **TODO:** Implementar estilos consistentes con CargarActuaciones

---

### 5. Vista Principal Refactorizada
**Archivo:** `Frontend/src/Containers/Actuaciones/index.tsx`

**Rol:** Orquestador

**Funcionalidades:**
- ✅ Maneja estado de filtros
- ✅ Usa hook `useActuacionesFiltradas`
- ✅ Pasa datos a componentes hijos (`FiltroFechas`, `TablaActuaciones`)
- ⚠️ **TODO:** Mostrar error y metadata de forma elegante

---

### 6. Tabla (Pendiente Refactorización)
**Archivo:** `Frontend/src/Containers/Actuaciones/Components/TableActuaciones.tsx`

- ⚠️ **TODO:** Modificar para recibir `data` como prop en lugar de usar hook interno
- ⚠️ **TODO:** Aceptar prop `onRefresh` para refrescar después de editar/eliminar

**Cambio sugerido:**
```typescript
interface TablaActuacionesProps {
    data: IActuacionListItem[];
    loading: boolean;
    onRefresh?: () => void;
}
```

---

## 🔧 ENUMS BACKEND

**Archivo:** `Backend/app/models/enums.py`

### Tipo (Enum)
```python
class Tipo(enum.Enum):
    INSPECCION = "INSPECCION"
    REINSPECCION = "REINSPECCION"
    RATIFICACION_CLAUSURA = "RATIFICACION DE CLAUSURA"
    RATIFICACION_DECOMISO = "RATIFICACION DE DECOMISO"
    VERIFICAR_E_INFORMAR = "VERIFICAR E INFORMAR"
    TRANSPORTE = "TRANSPORTE"
```

### Contraproducencia (ContraEnum)
```python
class ContraEnum(enum.Enum):
    LOCAL_CERRADO = "LOCAL CERRADO"
    NO_EXISTE = "NO EXISTE/NO ES EL RUBRO"
    INCLEMENCIA_TIEMPO = "CLIMA"
    ZONA_ROJA = "ZONA ROJA"
    NO_HUBO = "NO_HUBO"
    OTROS = "OTROS"
```

---

## 📐 ARQUITECTURA

```
┌─────────────────────────────────────────────────────────┐
│          FRONTEND: Actuaciones Container                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │   index.tsx (Orquestador)                       │   │
│  │   - Estado de filtros                           │   │
│  │   - Hook useActuacionesFiltradas()              │   │
│  └────────┬───────────────────────────┬─────────────┘   │
│           │                           │                 │
│  ┌────────▼────────┐        ┌────────▼──────────────┐  │
│  │ FiltroFechas    │        │ TablaActuaciones      │  │
│  │ (componente     │        │ (tabla editable)      │  │
│  │  reutilizable)  │        │ [TODO: refactorizar]  │  │
│  └─────────────────┘        └───────────────────────┘  │
│                                                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       │ GET /actuaciones?desde=...&tipo=...
                       ▼
┌─────────────────────────────────────────────────────────┐
│          BACKEND: Dominio actuaciones                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  routes/list.py                                          │
│       ↓                                                  │
│  schemas/list_filters.py (Pydantic validation)          │
│       ↓                                                  │
│  services/list_service.py (query + filtros + defaults)  │
│       ↓                                                  │
│  presenters/list_item.py (DTO simplificado)             │
│       ↓                                                  │
│  JSON Response { items: [...], meta: {...} }            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ COMPORTAMIENTO DE FILTROS

### Defaults de fechas:
1. **Si `desde` y `hasta` vacíos** → mes corriente
2. **Si solo `desde`** → hasta = hoy
3. **Si solo `hasta`** → desde = primer día del mes de `hasta`
4. **Validación:** `desde <= hasta`

### Filtro por Orden de Trabajo:
- Búsqueda exacta por número
- Si no existe → **raise `ValueError`** → response `400`

### Paginación:
- `page` >= 1
- `page_size` entre 1-500 (default: 50)

---

## 📝 PRÓXIMOS PASOS (TODO)

### Backend:
- ✅ Schema con defaults ✔️
- ✅ Service con filtros ✔️
- ✅ Presenter list_item ✔️
- ✅ Route refactorizada ✔️

### Frontend:
1. ⚠️ **Refactorizar `TableActuaciones.tsx`** para recibir `data` como prop
2. ⚠️ **Implementar estilos Neo-Brutalistas** en `FiltroFechas.tsx`
3. ⚠️ **Mostrar error elegantemente** en `index.tsx`
4. ⚠️ **Mostrar metadata** (total, página, rango de fechas aplicado)
5. ⚠️ **Agregar paginación UI** (botones prev/next, selector de página)
6. ⚠️ **Agregar loading skeleton** mientras carga

---

## 🧪 TESTING

### Backend (ejemplo con curl):
```bash
# Sin filtros (mes corriente por default)
curl "http://localhost:5000/actuaciones"

# Con rango de fechas
curl "http://localhost:5000/actuaciones?desde=2025-01-01&hasta=2025-01-31"

# Con tipo y contraproducencia
curl "http://localhost:5000/actuaciones?tipo=INSPECCION&contraproducencia=LOCAL%20CERRADO"

# Por orden de trabajo
curl "http://localhost:5000/actuaciones?orden_trabajo=123"

# Con paginación
curl "http://localhost:5000/actuaciones?page=2&page_size=20"
```

### Frontend:
- Verificar que filtros se apliquen correctamente
- Verificar defaults de fecha (mes corriente)
- Verificar manejo de error (orden de trabajo no existe)
- Verificar paginación

---

## 🎉 RESUMEN

✅ **Backend:** Totalmente implementado y funcional  
⚠️ **Frontend:** Estructura creada, pendiente implementación UI completa

**Arquitectura respetada:**
- ✅ Separación por dominios
- ✅ Routes delegan a Services
- ✅ Services aplican lógica de negocio
- ✅ Presenters transforman salida
- ✅ Schemas validan entrada
- ✅ Componentes modulares reutilizables
