"""
Fixtures controlados para OPER-ANALYTICS.2 (golden dataset).

Período aislado: marzo 2098. No usar en producción.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.database import db
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno
from tests.helpers.fixture_isolation import (
    fecha_fixture_aislada,
    uniq_ruta_numero,
    unique_ot_numero,
)
from tests.indicadores_cierre_fixtures import (
    vincular_cierre_realizado,
    vincular_ruta_en_proceso,
)

def periodo_golden(fecha_ruta: date) -> tuple[date, date]:
    """Rango canónico de prueba (día único aislado por corrida)."""
    return fecha_ruta, fecha_ruta


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"u_golden_{suf}",
        email=f"golden_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_inspector(nombre: str) -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(nombre=nombre, legajo=unique_ot_numero()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_domicilio(
    *,
    calle: str,
    distrito_id: int | None = None,
    with_geo_ok: bool = False,
) -> Domicilio:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=f"RubGolden_{uuid4().hex[:6]}")
        db.session.add(rub)
        db.session.flush()
    c = Contribuyente(
        apellido="Golden",
        nombre="T",
        documento=str(abs(hash(calle)) % 90_000_000 + 10_000_000),
    )
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=calle,
        numero="100",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    if with_geo_ok:
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status="OK",
            lat=-26.8241,
            lng=-65.2226,
            score=0.99,
            source="AUTO",
        )
        db.session.add(geo)
        db.session.flush()
    return dom


def _mk_actuacion(
    fecha: date,
    domicilio_id: int,
    *,
    tipo: str = "INSPECCION",
    contraproducencia: str | None = None,
    realizo_nueva_inspeccion: bool | None = None,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo=tipo,
        orden_trabajo_id=ot.id,
        domicilio_id=domicilio_id,
        contraproducencia=contraproducencia,
        realizo_nueva_inspeccion=realizo_nueva_inspeccion,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _vincular_no_realizado_canonico(
    act: Actuaciones,
    fecha_ruta: date,
    *,
    tipo_iniciador: str,
    contraproducencia: str = "LOCAL CERRADO",
    motivo: str = "LOCAL_CERRADO",
) -> RutaItem:
    """Cierre NO_REALIZADO con par canónico FINALIZADO + NO_REALIZADO."""
    u = _mk_user()
    fr = fecha_ruta
    act.contraproducencia = contraproducencia
    from app.models import IniciadorRuta, RutaTrabajo

    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador="PENDIENTE",
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
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="NO_REALIZADO",
        motivo_no_realizado=motivo,
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=datetime(fr.year, fr.month, fr.day, 12, 0, 0),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _vincular_legacy_no_realizado_item_estado(act: Actuaciones, fecha_ruta: date) -> RutaItem:
    """Legado estado_ruta_item=NO_REALIZADO (no debe entrar al universo canónico)."""
    from tests.indicadores_cierre_fixtures import vincular_cierre_no_realizado

    return vincular_cierre_no_realizado(
        act,
        fecha_ruta,
        tipo_iniciador="RELEVAMIENTO",
        contraproducencia="CLIMA",
    )


@dataclass
class GoldenFixtureWorld:
    """IDs de referencia tras sembrar el mundo golden."""

    relevamiento_realizado_geo: int
    denuncia_realizado_sin_geo: int
    rn_no_realizado_geo: int
    verificar_con_inspeccion: int
    verificar_sin_inspeccion: int
    ratif_clausura_no_realizado: int
    reintento_1: int
    reintento_2: int
    documental_actuacion_id: int
    planning_item_id: int
    legacy_no_realizado_item_id: int
    tres_inspectores_item_id: int
    fecha_discrepante_item_id: int
    distrito_discrepante_item_id: int
    fecha_ruta: date
    expected_universe_ids: list[int]


def seed_golden_world() -> GoldenFixtureWorld:
    """
    Siembra escenarios mínimos del ticket OPER-ANALYTICS.2.

    Retorno:
        Referencias a ``ruta_item_id`` / actuación para asserts.
    """
    fecha_ruta = fecha_fixture_aislada(anio=2098)
    dist_a = Distrito.query.first()
    dist_b = Distrito.query.offset(1).first() if Distrito.query.count() > 1 else dist_a

    dom_geo = _mk_domicilio(calle=f"GoldenGeo_{uuid4().hex[:6]}", with_geo_ok=True)
    dom_sin_geo = _mk_domicilio(calle=f"GoldenSinGeo_{uuid4().hex[:6]}", with_geo_ok=False)
    dom_rn = _mk_domicilio(
        calle=f"GoldenRN_{uuid4().hex[:6]}",
        with_geo_ok=True,
        distrito_id=dist_a.id if dist_a else None,
    )
    dom_reintento = _mk_domicilio(calle=f"GoldenReint_{uuid4().hex[:6]}", with_geo_ok=True)

    dom_act_dist = _mk_domicilio(
        calle=f"GoldenActDist_{uuid4().hex[:6]}",
        distrito_id=dist_a.id if dist_a else None,
        with_geo_ok=True,
    )
    dom_ini_dist = _mk_domicilio(
        calle=f"GoldenIniDist_{uuid4().hex[:6]}",
        distrito_id=dist_b.id if dist_b else None,
        with_geo_ok=True,
    )

    # 1 relevamiento REALIZADO con geo
    act_rel = _mk_actuacion(fecha_ruta, dom_geo.id)
    item_rel = vincular_cierre_realizado(
        act_rel, fecha_ruta, tipo_iniciador="RELEVAMIENTO", fecha_ruta=fecha_ruta
    )

    # 2 denuncia REALIZADO sin geo
    act_den = _mk_actuacion(fecha_ruta, dom_sin_geo.id, tipo="INSPECCION")
    item_den = vincular_cierre_realizado(
        act_den, fecha_ruta, tipo_iniciador="DENUNCIA", fecha_ruta=fecha_ruta
    )

    # 3 RN NO_REALIZADO con geo
    act_rn = _mk_actuacion(fecha_ruta, dom_rn.id, tipo="REINSPECCION")
    item_rn = _vincular_no_realizado_canonico(
        act_rn,
        fecha_ruta,
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        contraproducencia="LOCAL CERRADO",
    )

    # 4 verificar REALIZADO + inspección
    dom_vi_si = _mk_domicilio(calle=f"GoldenVISi_{uuid4().hex[:6]}", with_geo_ok=True)
    act_vi_si = _mk_actuacion(
        fecha_ruta,
        dom_vi_si.id,
        tipo="VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion=True,
    )
    attach_inspeccion(act_vi_si, unique_ot_numero())
    item_vi_si = vincular_cierre_realizado(
        act_vi_si,
        fecha_ruta,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        fecha_ruta=fecha_ruta,
    )

    # 5 verificar REALIZADO sin inspección
    dom_vi_no = _mk_domicilio(calle=f"GoldenVINo_{uuid4().hex[:6]}", with_geo_ok=True)
    act_vi_no = _mk_actuacion(
        fecha_ruta,
        dom_vi_no.id,
        tipo="VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion=False,
    )
    item_vi_no = vincular_cierre_realizado(
        act_vi_no,
        fecha_ruta,
        tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        fecha_ruta=fecha_ruta,
    )

    # 6 ratif clausura NO_REALIZADO
    dom_rat = _mk_domicilio(calle=f"GoldenRat_{uuid4().hex[:6]}", with_geo_ok=True)
    act_rat = _mk_actuacion(fecha_ruta, dom_rat.id, tipo="RATIFICACION DE CLAUSURA")
    item_rat = _vincular_no_realizado_canonico(
        act_rat,
        fecha_ruta,
        tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
        contraproducencia="NO SE RATIFICO",
        motivo="OTRO",
    )

    # 7 reintento mismo domicilio (2 intentos)
    act_r1 = _mk_actuacion(fecha_ruta, dom_reintento.id)
    item_r1 = _vincular_no_realizado_canonico(
        act_r1, fecha_ruta, tipo_iniciador="RELEVAMIENTO", contraproducencia="LOCAL CERRADO"
    )
    act_r2 = _mk_actuacion(fecha_ruta, dom_reintento.id)
    item_r2 = vincular_cierre_realizado(
        act_r2, fecha_ruta, tipo_iniciador="RELEVAMIENTO", fecha_ruta=fecha_ruta
    )

    # 8 documental sin RutaItem
    act_doc = _mk_actuacion(fecha_ruta, dom_geo.id)

    # 9 planning-only EN_PROCESO
    act_plan = _mk_actuacion(fecha_ruta, dom_geo.id)
    item_plan = vincular_ruta_en_proceso(act_plan, fecha_ruta)

    # legacy estado_ruta_item NO_REALIZADO (excluido)
    act_leg = _mk_actuacion(fecha_ruta, dom_geo.id)
    item_leg = _vincular_legacy_no_realizado_item_estado(act_leg, fecha_ruta)

    # tres inspectores, 1 intento
    dom_ins = _mk_domicilio(calle=f"Golden3Insp_{uuid4().hex[:6]}", with_geo_ok=True)
    act_ins = _mk_actuacion(fecha_ruta, dom_ins.id)
    i1, i2, i3 = (
        _mk_inspector("InspGolden1"),
        _mk_inspector("InspGolden2"),
        _mk_inspector("InspGolden3"),
    )
    for ins in (i1, i2, i3):
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act_ins.id,
                inspector_id=ins.id,
            )
        )
    attach_decomiso(act_ins, {"acta_num": unique_ot_numero(), "kilos_total": 12.5})
    item_ins = vincular_cierre_realizado(
        act_ins, fecha_ruta, tipo_iniciador="RELEVAMIENTO", fecha_ruta=fecha_ruta
    )

    # fecha ruta ≠ ejecutado
    dom_fecha = _mk_domicilio(calle=f"GoldenFecha_{uuid4().hex[:6]}", with_geo_ok=True)
    act_fecha = _mk_actuacion(fecha_ruta, dom_fecha.id)
    fecha_ejec = fecha_ruta + timedelta(days=7)
    item_fecha = vincular_cierre_realizado(
        act_fecha,
        fecha_ruta,
        tipo_iniciador="RELEVAMIENTO",
        fecha_ruta=fecha_ruta,
        fecha_ejecutado=fecha_ejec,
    )

    # distrito act vs ini
    act_dist = _mk_actuacion(fecha_ruta, dom_act_dist.id)
    item_dist = vincular_cierre_realizado(
        act_dist,
        fecha_ruta,
        tipo_iniciador="RELEVAMIENTO",
        fecha_ruta=fecha_ruta,
        ini_domicilio_id=dom_ini_dist.id,
    )

    db.session.flush()

    expected = [
        item_rel.id,
        item_den.id,
        item_rn.id,
        item_vi_si.id,
        item_vi_no.id,
        item_rat.id,
        item_r1.id,
        item_r2.id,
        item_ins.id,
        item_fecha.id,
        item_dist.id,
    ]

    return GoldenFixtureWorld(
        relevamiento_realizado_geo=item_rel.id,
        denuncia_realizado_sin_geo=item_den.id,
        rn_no_realizado_geo=item_rn.id,
        verificar_con_inspeccion=item_vi_si.id,
        verificar_sin_inspeccion=item_vi_no.id,
        ratif_clausura_no_realizado=item_rat.id,
        reintento_1=item_r1.id,
        reintento_2=item_r2.id,
        documental_actuacion_id=act_doc.id,
        planning_item_id=item_plan.id,
        legacy_no_realizado_item_id=item_leg.id,
        tres_inspectores_item_id=item_ins.id,
        fecha_discrepante_item_id=item_fecha.id,
        distrito_discrepante_item_id=item_dist.id,
        fecha_ruta=fecha_ruta,
        expected_universe_ids=expected,
    )
