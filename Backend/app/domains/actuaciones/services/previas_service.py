from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Actuaciones, Comprobacion, Notificacion
from app.utils.actas import acta_6


def resolver_previas(act: Actuaciones, payload: Dict[str, Any]) -> None:
    """
    Resuelve (modo upsert) las referencias a *actas previas* cargadas en el payload y las asocia
    a la actuación recibida.

    Qué hace:
    - Si `payload` trae un número de **Notificación previa** (`notificacion_previa_num` o
      `acta_notificacion_previa_num`):
        - Busca `Notificacion` por `(numero_acta, anio)` usando el `anio/mes` de `act`.
        - Si no existe, la crea de forma mínima (sin motivos) con `mes=act.mes`.
        - Asigna `act.notificacion_id`.

    - Si `payload` trae un número de **Comprobación previa** (`comprobacion_previa_num` o
     
      `acta_comprobacion_previa_num`):
        - Busca `Comprobacion` por `(numero_acta, anio)` usando el `anio/mes` de `act`.
        - Si no existe, la crea de forma mínima con `mes=act.mes` y `motivo`:
            - `payload["comprobacion_previa_motivo"]` si viene y no está vacío, o
            - `"PENDIENTE"` como placeholder explícito.
        - Si existe y viene `comprobacion_previa_motivo`, actualiza `motivo` (y `mes`).
        - Asigna `act.comprobacion_id`.

    Parámetros:
    - act: instancia de `Actuaciones` ya persistida/flush (necesita `anio`/`mes` coherentes).
    - payload: dict canon (del mapper) con campos opcionales de previas.

    Errores:
    - Puede propagar excepciones de DB (p.ej. integridad) durante `flush()` si el modelo exige
      constraints adicionales.
    """
    anio = act.anio
    mes = act.mes

    # -------------------------
    # NOTIFICACION PREVIA
    # -------------------------
    prev_noti_num = acta_6(payload.get("notificacion_previa_num") or payload.get("acta_notificacion_previa_num"))
    if prev_noti_num:
        noti = Notificacion.query.filter_by(numero_acta=prev_noti_num, anio=anio).first()
        if not noti:
            # crear previa mínima (sin motivos)
            noti = Notificacion(numero_acta=prev_noti_num, anio=anio, mes=mes)
            db.session.add(noti)
            db.session.flush()
        act.notificacion_id = noti.id

    # -------------------------
    # COMPROBACION PREVIA
    # -------------------------
    prev_comp_num = acta_6(payload.get("comprobacion_previa_num") or payload.get("acta_comprobacion_previa_num"))
    if prev_comp_num:
        comp = Comprobacion.query.filter_by(numero_acta=prev_comp_num, anio=anio).first()

        motivo_prev = (payload.get("comprobacion_previa_motivo") or "").strip()

        if not comp:
            # ⚠️ si motivo es NOT NULL en DB, usá un placeholder explícito
            # mejor "PENDIENTE" o "SIN_DATO" que "default"
            motivo_inicial = motivo_prev if motivo_prev else "PENDIENTE"
            comp = Comprobacion(numero_acta=prev_comp_num, anio=anio, mes=mes, motivo=motivo_inicial)
            db.session.add(comp)
            db.session.flush()
        else:
            # si existe y me pasaron motivo_prev, actualizo; si no, no toco
            if motivo_prev:
                comp.motivo = motivo_prev
                comp.mes = mes
                db.session.add(comp)

        act.comprobacion_id = comp.id
