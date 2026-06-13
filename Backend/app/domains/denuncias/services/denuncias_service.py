from __future__ import annotations

from datetime import date
from datetime import datetime

from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from app.database import db
from app.models import Denuncia, Domicilio, IniciadorRuta, User
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_domicilio_if_orphan,
)
from app.shared.services.domicilio_repo import get_or_create_domicilio_basico
from app.domains.domicilios.services.domicilio_update_service import aplicar_edicion_domicilio_operativo
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)
from app.domains.denuncias.schemas import DenunciasGestionFilters, DenunciaGestionRowIn
from app.domains.denuncias.services.operational_guard_service import (
    get_iniciador_pendiente_denuncia,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    is_estado_activo,
    priority_for_tipo,
)
from app.utils.iniciador_estado import es_estado_iniciador_pendiente, normalize_estado_iniciador


def _get_current_user_id() -> int:
    """
    Resuelve el usuario desde el JWT (subject = id numérico, ver ``login_user``).

    Raises:
        ValueError: identidad inválida, usuario inexistente o inactivo (mensaje ``Usuario no autorizado``).
    """
    identity = get_jwt_identity()
    if identity is None:
        raise ValueError("Usuario no autorizado.")
    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    try:
        parsed_id = int(str(user_id).strip())
    except (TypeError, ValueError):
        raise ValueError("Usuario no autorizado.")

    user = User.query.get(parsed_id)
    if not user or not user.is_active:
        raise ValueError("Usuario no autorizado.")
    return parsed_id


def _validar_exactamente_un_origen(**origenes: int | None) -> None:
    count = sum(1 for v in origenes.values() if v is not None)
    if count != 1:
        raise ValueError("iniciador_ruta debe tener exactamente un origen lógico.")


def _resolver_domicilio_id(
    *, domicilio_id: int | None, calle: str | None, numero: str | None, interseccion: str | None
) -> int:
    if domicilio_id:
        dom = Domicilio.query.get(domicilio_id)
        if not dom or dom.deleted_at is not None:
            raise ValueError("Domicilio no encontrado.")
        return int(domicilio_id)

    if not calle:
        raise ValueError("Debe enviar domicilio_id o calle.")

    numero_final = (numero or interseccion or "").strip()
    if not numero_final:
        raise ValueError("Debe enviar número o intersección.")

    dom = get_or_create_domicilio_basico(calle.strip(), numero_final)
    numero_tipo_override = "NUMERO" if numero and str(numero).strip() else "ESQUINA"
    normalizar_domicilio_en_sesion(dom, override_numero_tipo=numero_tipo_override)
    db.session.commit()
    try:
        on_domicilio_changed(dom.id)
    except Exception:
        pass
    return dom.id


def crear_denuncia_con_iniciador(
    *,
    fecha: date,
    domicilio_id: int | None,
    calle: str | None,
    numero: str | None,
    interseccion: str | None,
    motivo: str,
) -> tuple[Denuncia, IniciadorRuta]:
    """
    Crea denuncia e iniciador_ruta en una sola transacción.

    Reglas:
    - Obtiene user autenticado desde JWT.
    - Deriva anio/mes desde fecha.
    - Crea iniciador_ruta tipo DENUNCIA con estado PENDIENTE.
    - Enforce exact-one origen lógico para iniciador_ruta.
    """
    user_id = _get_current_user_id()

    resolved_domicilio_id = _resolver_domicilio_id(
        domicilio_id=domicilio_id,
        calle=calle,
        numero=numero,
        interseccion=interseccion,
    )

    anio = int(fecha.year)
    mes = int(fecha.month)

    denuncia = Denuncia(
        fecha=fecha,
        anio=anio,
        mes=mes,
        domicilio_id=resolved_domicilio_id,
        motivo=motivo.strip(),
        estado="ABIERTA",
        created_by_user_id=user_id,
    )
    db.session.add(denuncia)
    db.session.flush()

    _validar_exactamente_un_origen(
        denuncia_id=denuncia.id,
        relevamiento_id=None,
        notificacion_id=None,
        comprobacion_id=None,
        oficio_id=None,
        actuacion_id=None,
    )

    iniciador = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha,
        anio=anio,
        mes=mes,
        domicilio_id=resolved_domicilio_id,
        prioridad=priority_for_tipo("DENUNCIA"),
        denuncia_id=denuncia.id,
        created_by_user_id=user_id,
    )
    db.session.add(iniciador)
    db.session.commit()
    return denuncia, iniciador


def listar_denuncias(*, limit: int = 200) -> list[dict]:
    """
    Lista denuncias recientes con iniciador_ruta asociado (si existe).
    """
    rows = (
        Denuncia.query.filter(Denuncia.deleted_at.is_(None))
        .order_by(Denuncia.id.desc())
        .limit(limit)
        .all()
    )
    out: list[dict] = []
    for d in rows:
        data = d.to_dict()
        iniciador = (
            IniciadorRuta.query.filter(
                IniciadorRuta.denuncia_id == d.id,
                IniciadorRuta.deleted_at.is_(None),
            )
            .order_by(IniciadorRuta.id.desc())
            .first()
        )
        data["iniciador_ruta_id"] = iniciador.id if iniciador else None
        out.append(data)
    return out


def eliminar_denuncia_logicamente(denuncia_id: int) -> dict:
    """
    Soft delete de denuncia y de sus iniciadores activos.

    Regla:
    - No borra físicamente.
    - Si el domicilio queda huérfano luego del soft delete, lo marca deleted_at
      y también soft-delete del geocode asociado.
    """
    _get_current_user_id()
    denuncia = (
        Denuncia.query.filter(
            Denuncia.id == denuncia_id,
            Denuncia.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not denuncia:
        raise ValueError("Denuncia no encontrada.")

    get_iniciador_pendiente_denuncia(denuncia_id)

    now = datetime.utcnow()
    domicilio_id = denuncia.domicilio_id

    iniciadores = (
        IniciadorRuta.query.filter(
            IniciadorRuta.denuncia_id == denuncia.id,
            IniciadorRuta.deleted_at.is_(None),
        )
        .all()
    )
    for ini in iniciadores:
        ini.deleted_at = now
        if is_estado_activo(ini.estado_iniciador):
            ini.estado_iniciador = "ANULADO"
        ini.cerrado_at = ini.cerrado_at or now
        ini.cerrado_motivo = ini.cerrado_motivo or "SOFT_DELETE_DENUNCIA"
        db.session.add(ini)

    denuncia.deleted_at = now
    if denuncia.estado != "CERRADA":
        denuncia.estado = "DESCARTADA"
    db.session.add(denuncia)
    db.session.commit()

    soft_delete_domicilio_if_orphan(domicilio_id)
    db.session.commit()

    return {"ok": True, "denuncia_id": denuncia_id}


def _denuncia_to_gestion_row(
    d: Denuncia, iniciador: IniciadorRuta | None = None, *, bandeja_operativa: bool = False
) -> dict:
    dom = d.domicilio
    calle = getattr(dom, "calle", None)
    numero = getattr(dom, "numero", None)
    numero_tipo = getattr(dom, "numero_tipo", None)
    return {
        "id": d.id,
        "fecha": d.fecha.isoformat() if d.fecha else None,
        "calle": calle,
        "numero": numero,
        "numero_tipo": numero_tipo,
        "motivo": d.motivo,
        "estado": d.estado,
        "domicilio_id": d.domicilio_id,
        "iniciador_ruta_id": iniciador.id if iniciador else None,
        "iniciador_estado": normalize_estado_iniciador(iniciador.estado_iniciador) if iniciador else None,
        "editable": (
            True
            if bandeja_operativa and iniciador
            else (es_estado_iniciador_pendiente(iniciador.estado_iniciador) if iniciador else False)
        ),
    }


def listar_denuncias_gestion(filters: DenunciasGestionFilters) -> dict:
    """
    Listado de gestión de denuncias con filtros y paginación.
    """
    query = Denuncia.query.filter(Denuncia.deleted_at.is_(None))

    if filters.desde:
        query = query.filter(Denuncia.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Denuncia.fecha <= filters.hasta)

    # Regla de negocio UI:
    # - hechas: estado CERRADA
    # - no_hechas: todo lo no CERRADA (ABIERTA/DESCARTADA)
    if filters.estado == "hechas":
        query = query.filter(Denuncia.estado == "CERRADA")
    elif filters.estado == "no_hechas":
        query = query.filter(Denuncia.estado != "CERRADA")

    total = query.count()
    offset = (filters.page - 1) * filters.page_size
    items = (
        query.order_by(Denuncia.id.desc())
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )
    return {
        "items": [_denuncia_to_gestion_row(d) for d in items],
        "meta": {
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "desde": filters.desde.isoformat() if filters.desde else None,
            "hasta": filters.hasta.isoformat() if filters.hasta else None,
            "estado": filters.estado,
        },
    }


def listar_denuncias_gestion_operativa(filters: DenunciasGestionFilters) -> dict:
    """
    Listado operativo de denuncias:
    solo aquellas con iniciador DENUNCIA pendiente y activo.
    """
    pending_iniciador_subq = (
        db.session.query(
            IniciadorRuta.denuncia_id.label("denuncia_id"),
            func.max(IniciadorRuta.id).label("iniciador_id"),
        )
        .filter(
            IniciadorRuta.denuncia_id.isnot(None),
            IniciadorRuta.tipo_iniciador == "DENUNCIA",
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
        )
        .group_by(IniciadorRuta.denuncia_id)
        .subquery()
    )

    query = (
        db.session.query(Denuncia, IniciadorRuta)
        .join(pending_iniciador_subq, pending_iniciador_subq.c.denuncia_id == Denuncia.id)
        .join(IniciadorRuta, IniciadorRuta.id == pending_iniciador_subq.c.iniciador_id)
        .filter(Denuncia.deleted_at.is_(None))
    )

    if filters.desde:
        query = query.filter(Denuncia.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Denuncia.fecha <= filters.hasta)

    total = query.count()
    offset = (filters.page - 1) * filters.page_size
    rows = (
        query.order_by(Denuncia.id.desc())
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )
    return {
        "items": [_denuncia_to_gestion_row(d, iniciador, bandeja_operativa=True) for d, iniciador in rows],
        "meta": {
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "desde": filters.desde.isoformat() if filters.desde else None,
            "hasta": filters.hasta.isoformat() if filters.hasta else None,
            "estado": "operativas_pendientes",
        },
    }


def actualizar_denuncia_gestion(denuncia_id: int, row: DenunciaGestionRowIn) -> dict:
    """
    Actualiza denuncia desde grilla de gestión.
    """
    _get_current_user_id()
    denuncia = (
        Denuncia.query.filter(
            Denuncia.id == denuncia_id,
            Denuncia.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not denuncia:
        raise ValueError("Denuncia no encontrada.")

    iniciador_operativo = get_iniciador_pendiente_denuncia(denuncia_id)
    old_domicilio_id = denuncia.domicilio_id

    outcome = aplicar_edicion_domicilio_operativo(
        domicilio_id_actual=denuncia.domicilio_id,
        cambios={"calle": row.calle, "numero": row.numero, "numero_tipo": row.numero_tipo},
        contexto="DENUNCIA",
        origen_id=denuncia_id,
        modo_explicito=getattr(row, "modo_domicilio", None),
        usar_basico=True,
    )
    dom = outcome.domicilio
    if dom is None:
        raise ValueError("No se pudo resolver domicilio.")
    override = row.numero_tipo
    if not override:
        override = "ESQUINA" if any(ch.isalpha() for ch in row.numero) else "NUMERO"
    normalizar_domicilio_en_sesion(dom, override_numero_tipo=override)

    denuncia.fecha = row.fecha
    denuncia.anio = int(row.fecha.year)
    denuncia.mes = int(row.fecha.month)
    denuncia.domicilio_id = dom.id
    denuncia.motivo = row.motivo
    denuncia.estado = row.estado
    db.session.add(denuncia)

    iniciador_operativo.domicilio_id = dom.id
    db.session.add(iniciador_operativo)

    db.session.commit()

    if old_domicilio_id is not None and old_domicilio_id != denuncia.domicilio_id:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        db.session.commit()

    try:
        on_domicilio_changed(denuncia.domicilio_id)
    except Exception:
        pass

    refreshed_iniciador = get_iniciador_pendiente_denuncia(denuncia.id)
    return _denuncia_to_gestion_row(denuncia, refreshed_iniciador)
