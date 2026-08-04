"""Fixtures compartidas: cierres operativos REALIZADO para tests de indicadores."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    contraproducencia_es_familia_no_existe_local,
)
from app.models import (
    Actuaciones,
    IniciadorRuta,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
    actuaciones_inspector,
)
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero


def _unique_ot_num() -> str:
    return unique_ot_numero()


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"u_ind_{suf}",
        email=f"ind_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _as_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day, 10, 0, 0)


def vincular_cierre_realizado(
    act: Actuaciones,
    fecha_cierre: date,
    *,
    fecha_ruta: date | None = None,
    fecha_ejecutado: date | datetime | None = None,
    tipo_iniciador: str = "RELEVAMIENTO",
    ini_domicilio_id: int | None = None,
    inspector_id: int | None = None,
) -> RutaItem:
    """
    Crea ruta PUBLICADA + RutaItem FINALIZADO/REALIZADO vinculado a ``act``.

    Si ``act`` no tiene OT, crea una. Opcionalmente vincula inspector.
    """
    u = _mk_user()
    if act.orden_trabajo_id is None:
        ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=fecha_cierre.year, mes=fecha_cierre.month)
        db.session.add(ot)
        db.session.flush()
        act.orden_trabajo_id = ot.id
    dom_ini = ini_domicilio_id if ini_domicilio_id is not None else act.domicilio_id
    if dom_ini is None:
        raise ValueError(
            "vincular_cierre_realizado requiere domicilio_id en actuación o ini_domicilio_id"
        )
    fr = fecha_ruta if fecha_ruta is not None else fecha_cierre
    fe = fecha_ejecutado if fecha_ejecutado is not None else fecha_cierre
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador="CUMPLIDO",
        fecha_origen=fr,
        anio=fr.year,
        mes=fr.month,
        domicilio_id=dom_ini,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fr,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="REALIZADO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=_as_datetime(fe),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    if inspector_id is not None:
        existing = db.session.execute(
            actuaciones_inspector.select().where(
                actuaciones_inspector.c.actuaciones_id == act.id,
                actuaciones_inspector.c.inspector_id == inspector_id,
            )
        ).first()
        if existing is None:
            db.session.execute(
                actuaciones_inspector.insert().values(
                    actuaciones_id=act.id,
                    inspector_id=inspector_id,
                )
            )
    return item


def estado_iniciador_tras_no_realizado(contraproducencia: str) -> str:
    """Estado del iniciador tras Completar trabajo con contraproducencia dada."""
    if contraproducencia_es_familia_no_existe_local(contraproducencia):
        return "CERRADO_NO_EXISTE_LOCAL"
    return "PENDIENTE"


def vincular_cierre_no_realizado(
    act: Actuaciones,
    fecha_cierre: date,
    *,
    fecha_ruta: date | None = None,
    fecha_ejecutado: date | datetime | None = None,
    tipo_iniciador: str = "RELEVAMIENTO",
    contraproducencia: str = "LOCAL_CERRADO",
    estado_iniciador: str | None = None,
    inspector_id: int | None = None,
) -> RutaItem:
    """Crea cierre NO_REALIZADO con contraproducencia real vinculado a ``act``."""
    u = _mk_user()
    if act.orden_trabajo_id is None:
        ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=fecha_cierre.year, mes=fecha_cierre.month)
        db.session.add(ot)
        db.session.flush()
        act.orden_trabajo_id = ot.id
    if act.domicilio_id is None:
        raise ValueError("vincular_cierre_no_realizado requiere domicilio_id")
    act.contraproducencia = contraproducencia
    fr = fecha_ruta if fecha_ruta is not None else fecha_cierre
    fe = fecha_ejecutado if fecha_ejecutado is not None else fecha_cierre
    ini_estado = (
        estado_iniciador
        if estado_iniciador is not None
        else estado_iniciador_tras_no_realizado(contraproducencia)
    )
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador=ini_estado,
        fecha_origen=fr,
        anio=fr.year,
        mes=fr.month,
        domicilio_id=act.domicilio_id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fr,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="NO_REALIZADO",
        estado_ejecucion="NO_REALIZADO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=_as_datetime(fe),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    if inspector_id is not None:
        existing = db.session.execute(
            actuaciones_inspector.select().where(
                actuaciones_inspector.c.actuaciones_id == act.id,
                actuaciones_inspector.c.inspector_id == inspector_id,
            )
        ).first()
        if existing is None:
            db.session.execute(
                actuaciones_inspector.insert().values(
                    actuaciones_id=act.id,
                    inspector_id=inspector_id,
                )
            )
    return item


def vincular_ruta_en_proceso(
    act: Actuaciones,
    fecha_ruta: date,
    *,
    tipo_iniciador: str = "RELEVAMIENTO",
) -> RutaItem:
    """Ruta publicada con ítem EN_PROCESO (sin cierre)."""
    u = _mk_user()
    if act.orden_trabajo_id is None:
        ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=fecha_ruta.year, mes=fecha_ruta.month)
        db.session.add(ot)
        db.session.flush()
        act.orden_trabajo_id = ot.id
    if act.domicilio_id is None:
        raise ValueError("vincular_ruta_en_proceso requiere domicilio_id")
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador="EN_EJECUCION",
        fecha_origen=fecha_ruta,
        anio=fecha_ruta.year,
        mes=fecha_ruta.month,
        domicilio_id=act.domicilio_id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha_ruta,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    return item
