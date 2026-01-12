# Refactor plan - actuaciones (scope limitado)

Solo se permite tocar:
- Backend/app/routes/actuaciones*
- Backend/app/services/actuaciones*
- Backend/app/utils/actas.py
- Backend/app/utils/fechas.py

No tocar otros módulos.
Refactor incremental + commits chicos.

Objetivo:
- eliminar mega-helper `actuacion_helpers.py`
- separar por dominio (attach por entidad + previas)
- separar services por acción (create/update/delete)
- modularizar routes (1 endpoint = 1 archivo)
- mantener mismo comportamiento y mismos endpoints
