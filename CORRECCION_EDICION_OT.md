# ✅ CORRECCIÓN - EDICIÓN DE ORDEN DE TRABAJO (NO CREAR NUEVAS)

## 🐛 Problema Identificado

**Al editar orden_trabajo_numero:**
- Se creaba una nueva OT en lugar de buscar una existente
- Causaba duplicación de OTs innecesarias
- Violaba la intención del usuario (solo quiere reasignar a OT existente)

**Causa raíz:**
El código original usaba `get_or_create_orden_trabajo()` que **crea** una nueva OT si no existe.

## 🔧 Solución Implementada

### Regla de Negocio Aplicada:

**En PATCH (edición):**
- ✅ Solo buscar OTs existentes
- ❌ NO crear nuevas OTs
- ✅ Normalizar número con `acta_6()` (ej: "123" → "000123")
- ✅ Validar regla: 1 actuación por OT
- ✅ Mensaje de error claro si OT no existe

**En POST/PUT (creación/carga masiva):**
- ✅ Sigue creando OTs nuevas si no existen
- ✅ Sin cambios en el flujo existente

### Código Agregado en `patch_service.py`:

```python
# Orden de Trabajo (solo buscar existente, NO crear nueva)
if "orden_trabajo_numero" in patch_dict:
    from app.models import OrdenTrabajo
    from app.utils.actas import acta_6
    
    # Normalizar número de OT
    ot_numero_normalizado = acta_6(patch_dict["orden_trabajo_numero"])
    
    # Buscar OT existente (NO crear nueva)
    ot = OrdenTrabajo.query.filter_by(numero=ot_numero_normalizado).first()
    
    if not ot:
        raise ValueError(
            f"Orden de Trabajo '{patch_dict['orden_trabajo_numero']}' "
            f"(normalizado: '{ot_numero_normalizado}') no existe. "
            f"No se pueden crear nuevas OTs al editar. "
            f"Usa el grid de carga para crear actuaciones con nuevas OTs."
        )
    
    # Validar regla: 1 actuación por OT
    if ot.id != act.orden_trabajo_id:
        # Verificar que no haya otra actuación con esa OT
        otra_act = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
        if otra_act and otra_act.id != actuacion_id:
            raise ValueError(
                f"Ya existe otra actuación (ID: {otra_act.id}) "
                f"asociada a la OT '{ot_numero_normalizado}'. "
                f"Cada OT solo puede tener una actuación."
            )
        
        # Asignar nueva OT
        act.orden_trabajo_id = ot.id
```

## 🎯 Comportamiento Ahora

### Caso 1: Editar OT a una existente ✅

```
Actuación actual: OT = "000123"
Usuario edita: orden_trabajo_numero = "456"

Backend:
1. Normaliza "456" → "000456"
2. Busca OT "000456" en DB
3. Encuentra OT existente ✅
4. Verifica que no haya otra actuación con esa OT ✅
5. Asigna nueva OT a la actuación
6. Commit

Resultado: Actuación ahora tiene OT = "000456"
```

### Caso 2: Editar OT a una que no existe ❌

```
Actuación actual: OT = "000123"
Usuario edita: orden_trabajo_numero = "999999"

Backend:
1. Normaliza "999999" → "999999"
2. Busca OT "999999" en DB
3. NO encuentra ❌
4. Lanza error 400:
   "Orden de Trabajo '999999' (normalizado: '999999') no existe.
    No se pueden crear nuevas OTs al editar.
    Usa el grid de carga para crear actuaciones con nuevas OTs."

Resultado: Error, actuación NO se modifica
```

### Caso 3: Editar OT a una que ya tiene otra actuación ❌

```
Actuación actual: ID=10, OT = "000123"
Otra actuación: ID=20, OT = "000456"
Usuario edita actuación 10: orden_trabajo_numero = "456"

Backend:
1. Normaliza "456" → "000456"
2. Busca OT "000456" en DB
3. Encuentra OT existente ✅
4. Verifica si otra actuación tiene esa OT
5. Encuentra actuación ID=20 con esa OT ❌
6. Lanza error 400:
   "Ya existe otra actuación (ID: 20) asociada a la OT '000456'.
    Cada OT solo puede tener una actuación."

Resultado: Error, actuación NO se modifica (regla de negocio)
```

### Caso 4: Crear actuación nueva (grid de carga) ✅

```
Grid de carga masiva usa PUT /actuaciones

Backend:
1. Usa update_service.py (no patch_service.py)
2. Llama get_or_create_orden_trabajo()
3. Si OT no existe → la crea ✅
4. Asigna OT a actuación
5. Commit

Resultado: Nueva actuación con nueva OT creada
```

## 📋 Validaciones Aplicadas

### 1. ✅ Normalización con `acta_6()`
- "123" → "000123"
- "1" → "000001"
- "999999" → "999999"

### 2. ✅ OT debe existir previamente
- Solo permite asignar a OTs que ya están en la DB
- NO crea nuevas OTs al editar

### 3. ✅ Regla: 1 actuación por OT
- No permite reasignar una OT que ya tiene otra actuación
- Valida antes de asignar

### 4. ✅ Mensajes de error claros
- Indica qué OT no existe
- Muestra número normalizado
- Explica cómo crear nuevas OTs (usar grid de carga)

## 📂 Archivos Modificados

**Backend:**
- ✅ `Backend/app/domains/actuaciones/services/patch_service.py`
  - Agregada lógica para manejar `orden_trabajo_numero`
  - Solo busca OTs existentes (NO crea nuevas)
  - Valida regla 1 actuación por OT

## ✅ Estado Final

✅ **PATCH - Editar OT:** Solo busca existentes, NO crea nuevas  
✅ **PUT/POST - Crear:** Sigue creando OTs nuevas (sin cambios)  
✅ **Normalización:** Usa `acta_6()` para buscar correctamente  
✅ **Validación:** 1 actuación por OT aplicada  
✅ **Mensajes claros:** Explica qué hacer si OT no existe  

## 🧪 Para Testear

### Test 1: Editar OT a una existente
```
1. Crear dos actuaciones:
   - Actuación A: OT = "000100"
   - Actuación B: OT = "000200"

2. Editar Actuación A:
   - Cambiar orden_trabajo_numero = "200"

3. Verificar:
   - Error 400: "Ya existe otra actuación asociada a la OT '000200'" ✅
```

### Test 2: Editar OT a una que no existe
```
1. Editar actuación:
   - Cambiar orden_trabajo_numero = "999999"

2. Verificar:
   - Error 400: "Orden de Trabajo '999999' no existe..." ✅
   - Mensaje sugiere usar grid de carga ✅
```

### Test 3: Editar OT a una existente y libre
```
1. Crear actuaciones:
   - Actuación A: OT = "000100"
   - OT "000300" existe pero sin actuaciones

2. Editar Actuación A:
   - Cambiar orden_trabajo_numero = "300"

3. Verificar:
   - Actualización exitosa ✅
   - Actuación A ahora tiene OT = "000300" ✅
```

### Test 4: Crear nueva actuación en grid de carga
```
1. Ir a "Cargar Actuaciones"
2. Crear fila con OT nueva "000500"
3. Guardar

4. Verificar:
   - OT "000500" se crea automáticamente ✅
   - Actuación se crea con esa OT ✅
```

## 🚀 PROBLEMA RESUELTO!

Ahora al editar:
- ✅ NO se crean OTs duplicadas
- ✅ Solo se asignan OTs existentes
- ✅ Se valida regla de negocio (1 actuación por OT)
- ✅ Mensajes claros si OT no existe

**¡La edición de OT ahora funciona correctamente sin crear duplicados!** 🎉
