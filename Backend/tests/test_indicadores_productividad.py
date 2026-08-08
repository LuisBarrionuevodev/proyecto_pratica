"""
GET /api/indicadores/productividad: realizadas, no realizadas y actas por inspector.
"""

from __future__ import annotations

import random
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_productividad_queries import (
    _no_realizadas_inspector_visita_pairs,
    format_contraproducencia_label,
    principal_bucket_label,
    query_inspectores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.domains.indicadores.utils.contraproducencia_indicador_buckets import BUCKET_ORDER
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from tests.helpers.fixture_isolation import unique_ot_numero
from tests.indicadores_cierre_fixtures import (
    estado_iniciador_tras_no_realizado,
    vincular_cierre_realizado,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Motivo,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_DESDE = date(2026, 8, 1)
_HASTA = date(2026, 8, 31)
_FECHA = date(2026, 8, 15)


def _unique_ot_num() -> str:
    return unique_ot_numero()


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{_unique_ot_num()}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"u_prod_{suf}",
        email=f"prod_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_inspector() -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(
        nombre=_unique_name("InspProd"),
        legajo=_unique_ot_num()[:5],
        turno_id=turno.id,
    )
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_visita_cierre(
    tipo_iniciador: str,
    fecha_cierre: date,
    *,
    realizada: bool = True,
    contraproducencia: str | None = None,
    inspector_id: int | None = None,
    distrito_id: int | None = None,
) -> tuple[RutaItem, Actuaciones, Inspector | None]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = _mk_user()
    ins = None
    if inspector_id is None:
        ins = _mk_inspector()
        inspector_id = ins.id
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Prod", nombre="T", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CalleProd"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_cierre,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        contraproducencia=contraproducencia,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    ini_estado = "CUMPLIDO" if realizada else estado_iniciador_tras_no_realizado(
        contraproducencia or "LOCAL_CERRADO"
    )
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador=ini_estado,
        fecha_origen=fecha_cierre,
        anio=2026,
        mes=8,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha_cierre,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    if realizada:
        estado_ruta = "FINALIZADO"
        estado_ej = "REALIZADO"
    else:
        estado_ruta = "FINALIZADO"
        estado_ej = "NO_REALIZADO"
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item=estado_ruta,
        estado_ejecucion=estado_ej,
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=datetime(2026, 8, 15, 10, 0, 0),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    if ins is None and inspector_id is not None:
        ins = db.session.get(Inspector, inspector_id)
    return item, act, ins


def _mk_actuacion_con_inspector(
    fecha: date,
    inspector_id: int,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    return act


def _find_realizada(inspector_id: int, rows):
    return next((r for r in rows if r.inspector_id == inspector_id), None)


@pytest.mark.parametrize(
    "tipo_iniciador,field",
    [
        ("RELEVAMIENTO", "inspecciones"),
        ("REINSPECCION_OFICIO", "reinspecciones_oficio"),
        ("RATIFICACION_CLAUSURA_OFICIO", "reinspecciones_oficio"),
        ("RATIFICACION_DECOMISO_OFICIO", "reinspecciones_oficio"),
        ("VERIFICAR_INFORMAR_OFICIO", "reinspecciones_oficio"),
        ("REINSPECCION_NOTIFICACION", "reinspecciones_notificacion"),
        ("DENUNCIA", "denuncias"),
    ],
)
def test_realizada_suma_por_tipo(app_ctx, tipo_iniciador, field) -> None:
    try:
        _, _, ins = _mk_visita_cierre(tipo_iniciador, _FECHA, realizada=True)
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_realizadas)
        assert row is not None
        assert getattr(row, field) >= 1
        assert row.total_realizadas >= getattr(row, field)
        visible = (
            row.inspecciones
            + row.reinspecciones_oficio
            + row.reinspecciones_notificacion
            + row.otras
        )
        assert row.total_realizadas == visible
        if field == "denuncias":
            assert row.denuncias >= 1
            assert row.otras >= row.denuncias
    finally:
        db.session.rollback()


def test_ejecutivo_inspecciones_coincide_con_bucket_productividad(app_ctx) -> None:
    try:
        from app.domains.indicadores.services.indicadores_ejecutivo_service import (
            build_indicadores_ejecutivo,
        )
        from app.domains.indicadores.services.indicadores_productividad_queries import (
            count_visitas_realizadas_productividad_bucket,
        )

        _, _, ins = _mk_visita_cierre("RELEVAMIENTO", _FECHA, realizada=True)
        assert ins is not None
        db.session.flush()
        ej = build_indicadores_ejecutivo(_DESDE, _HASTA)
        bucket_count = count_visitas_realizadas_productividad_bucket(
            _DESDE, _HASTA, bucket="inspecciones"
        )
        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, prod.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones >= 1
        assert ej.kpis.inspecciones_realizadas == bucket_count
        assert bucket_count >= 1
    finally:
        db.session.rollback()


def test_no_realizada_oficio_hibrido_suma_bucket(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "RATIFICACION_CLAUSURA_OFICIO",
            _FECHA,
            realizada=False,
            contraproducencia="LOCAL_CERRADO",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas >= 1
        assert row.local_cerrado >= 1
    finally:
        db.session.rollback()


def test_no_realizada_suma_y_contraproducencia_principal(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="LOCAL_CERRADO",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas >= 1
        assert row.local_cerrado >= 1
        assert row.contraproducencia_principal == "Local cerrado"
        assert (
            row.local_cerrado
            + row.no_existe
            + row.no_se_ratifico
            + row.clima
            + row.otras
        ) == row.total_no_realizadas
    finally:
        db.session.rollback()


def test_no_existe_local_suma_productividad(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="NO_EXISTE_LOCAL",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas >= 1
        assert row.contraproducencia_principal == "No existe local"
    finally:
        db.session.rollback()


def test_no_hubo_no_suma(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "DENUNCIA",
            _FECHA,
            realizada=False,
            contraproducencia="NO_HUBO",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is None
    finally:
        db.session.rollback()


def test_principal_bucket_label_empate_prioridad() -> None:
    assert principal_bucket_label(
        {"inspecciones": 2, "reinspecciones_oficio": 2, "denuncias": 0, "reinspecciones_notificacion": 0}
    ) == "Inspección"
    assert format_contraproducencia_label("DOMICILIO_INCORRECTO") == "Domicilio incorrecto"


def _actuacion_con_cierre(inspector_id: int, fecha: date) -> Actuaciones:
    """Actuación con domicilio, inspector y cierre REALIZADO en fecha."""
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Actas", nombre="T", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=_unique_name("CalleActas"), numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    vincular_cierre_realizado(act, fecha, inspector_id=inspector_id)
    return act


def test_actas_notificacion_con_motivos(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        m = Motivo.query.first()
        if m is None:
            m = Motivo(nombre=_unique_name("MotProd"))
            db.session.add(m)
            db.session.flush()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.notificacion >= 1
        assert row.total_actas >= 1
    finally:
        db.session.rollback()


def test_actas_comprobacion_pendiente_no_suma(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        resolver_previas(
            act,
            {"comprobacion_previa_num": _unique_ot_num(), "comprobacion_previa_motivo": None},
        )
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is None or row.comprobacion == 0
    finally:
        db.session.rollback()


def test_actas_comprobacion_labrada(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        attach_comprobacion(act, {"acta_num": _unique_ot_num(), "motivo": "Falta higiene"})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.comprobacion >= 1
    finally:
        db.session.rollback()


def test_actas_clausura_y_decomiso(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act_c = _actuacion_con_cierre(ins.id, _FECHA)
        attach_clausura(act_c, {"acta_num": _unique_ot_num()})
        act_d = _actuacion_con_cierre(ins.id, date(2026, 8, 16))
        attach_decomiso(act_d, {"acta_num": _unique_ot_num(), "kilos_total": 5})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.clausura >= 1
        assert row.decomiso >= 1
        assert row.total_actas >= 2
    finally:
        db.session.rollback()


def test_filtro_inspector_id(app_ctx) -> None:
    try:
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        _mk_visita_cierre("RELEVAMIENTO", _FECHA, realizada=True, inspector_id=ins_a.id)
        _mk_visita_cierre("DENUNCIA", _FECHA, realizada=True, inspector_id=ins_b.id)
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA, inspector_id=ins_a.id)
        ids = {r.inspector_id for r in out.inspectores_realizadas}
        assert ids <= {ins_a.id}
        assert ins_a.id in ids
        assert ins_b.id not in ids
    finally:
        db.session.rollback()


def test_filtro_distrito_id(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos.")
        d_a, d_b = distritos[0], distritos[1]
        if d_a.id == d_b.id:
            pytest.skip("Se requieren 2 distritos distintos.")
        ins = _mk_inspector()
        _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=True,
            inspector_id=ins.id,
            distrito_id=d_a.id,
        )
        _mk_visita_cierre(
            "DENUNCIA",
            _FECHA,
            realizada=True,
            inspector_id=ins.id,
            distrito_id=d_b.id,
        )
        db.session.flush()
        out_a = build_indicadores_productividad(_DESDE, _HASTA, distrito_id=d_a.id)
        row = _find_realizada(ins.id, out_a.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones >= 1
        assert row.denuncias == 0
    finally:
        db.session.rollback()


def test_no_realizada_un_inspector_cuenta_una_vez(app_ctx) -> None:
    try:
        item, _act, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="LOCAL_CERRADO",
        )
        assert ins is not None
        db.session.flush()
        pairs = _no_realizadas_inspector_visita_pairs(_DESDE, _HASTA)
        assert sum(1 for ri, iid, *_ in pairs if iid == ins.id and ri == item.id) == 1
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas == 1
        assert row.local_cerrado == 1
    finally:
        db.session.rollback()


def test_no_realizada_dos_inspectores_misma_visita_cuenta_para_cada_uno(app_ctx) -> None:
    try:
        item, act, ins_a = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="LOCAL_CERRADO",
        )
        assert ins_a is not None
        ins_b = _mk_inspector()
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins_b.id,
            )
        )
        db.session.flush()
        pairs = _no_realizadas_inspector_visita_pairs(_DESDE, _HASTA)
        pair_keys = {(ri, iid) for ri, iid, *_ in pairs}
        assert (item.id, ins_a.id) in pair_keys
        assert (item.id, ins_b.id) in pair_keys
        assert len([1 for ri, iid in pair_keys if ri == item.id]) == 2

        out = build_indicadores_productividad(_DESDE, _HASTA)
        row_a = _find_realizada(ins_a.id, out.inspectores_no_realizadas)
        row_b = _find_realizada(ins_b.id, out.inspectores_no_realizadas)
        assert row_a is not None and row_b is not None
        assert row_a.total_no_realizadas == 1
        assert row_b.total_no_realizadas == 1
        assert row_a.local_cerrado == 1
        assert row_b.local_cerrado == 1
    finally:
        db.session.rollback()


def test_no_realizada_par_inspector_ruta_item_no_duplica(app_ctx) -> None:
    """Un segundo vínculo inspector-actuación no debe inflar el total del inspector."""
    try:
        item, act, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="CLIMA",
        )
        assert ins is not None
        ins_dup = _mk_inspector()
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins_dup.id,
            )
        )
        db.session.flush()
        before = query_inspectores_no_realizadas(_DESDE, _HASTA)
        row_before = _find_realizada(ins.id, before)
        assert row_before is not None
        assert row_before.total_no_realizadas == 1
        assert row_before.clima == 1
        assert (
            row_before.local_cerrado
            + row_before.no_existe
            + row_before.no_se_ratifico
            + row_before.clima
            + row_before.otras
        ) == row_before.total_no_realizadas
    finally:
        db.session.rollback()


def test_no_realizada_suma_por_inspector_puede_superar_total_general(app_ctx) -> None:
    """Visita con dos inspectores: total general 1, suma por inspector 2 (válido)."""
    try:
        _item, _act, ins_a = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="NO_EXISTE_LOCAL",
        )
        assert ins_a is not None
        ins_b = _mk_inspector()
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=_act.id,
                inspector_id=ins_b.id,
            )
        )
        db.session.flush()
        from app.domains.indicadores.services.indicadores_no_realizadas_service import (
            build_indicadores_no_realizadas,
        )

        general = build_indicadores_no_realizadas(_DESDE, _HASTA).total
        out = build_indicadores_productividad(_DESDE, _HASTA)
        suma = sum(r.total_no_realizadas for r in out.inspectores_no_realizadas)
        assert general >= 1
        assert suma >= 2
    finally:
        db.session.rollback()


def _assert_bucket_invariant(desde: date, hasta: date) -> None:
    """Ningún inspector puede superar el total general de un bucket de contraproducencia."""
    nr = build_indicadores_no_realizadas(desde, hasta)
    prod = build_indicadores_productividad(desde, hasta)
    general = {r.bucket: r.cantidad for r in nr.contraproducencias_resumen}
    for row in prod.inspectores_no_realizadas:
        for bucket in BUCKET_ORDER:
            inspector_val = int(getattr(row, bucket))
            general_val = int(general.get(bucket, 0))
            assert inspector_val <= general_val, (
                f"bucket={bucket} general={general_val} "
                f"inspector={row.inspector} valor={inspector_val}"
            )


def test_invariante_bucket_inspector_no_supera_general(app_ctx) -> None:
    try:
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="CLIMA",
            inspector_id=ins_a.id,
        )
        item2, act2, _ = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="CLIMA",
            inspector_id=ins_b.id,
        )
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act2.id,
                inspector_id=ins_a.id,
            )
        )
        db.session.flush()
        _assert_bucket_invariant(_DESDE, _HASTA)
        nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        general_clima = next(
            r.cantidad for r in nr.contraproducencias_resumen if r.bucket == "clima"
        )
        assert general_clima >= 2
        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row_a = _find_realizada(ins_a.id, prod.inspectores_no_realizadas)
        row_b = _find_realizada(ins_b.id, prod.inspectores_no_realizadas)
        assert row_a is not None and row_a.clima >= 1
        assert row_b is not None and row_b.clima >= 1
        assert row_a.clima <= general_clima
        assert row_b.clima <= general_clima
    finally:
        db.session.rollback()


def test_dos_ruta_items_misma_actuacion_cuentan_por_visita(app_ctx) -> None:
    """Varios ruta_item con la misma actuación: general y productividad cuentan visitas."""
    try:
        ins = _mk_inspector()
        item1, act, _ = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="CLIMA",
            inspector_id=ins.id,
        )
        u = _mk_user()
        rub = Rubro.query.first()
        assert rub is not None
        ini2 = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=_FECHA,
            anio=2026,
            mes=8,
            domicilio_id=act.domicilio_id,
            created_by_user_id=u.id,
        )
        db.session.add(ini2)
        db.session.flush()
        ruta2 = RutaTrabajo(
            fecha=_FECHA,
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=random.randint(2, 32000),
        )
        db.session.add(ruta2)
        db.session.flush()
        item2 = RutaItem(
            ruta_trabajo_id=ruta2.id,
            iniciador_ruta_id=ini2.id,
            orden_trabajo_id=act.orden_trabajo_id,
            estado_ruta_item="FINALIZADO",
            estado_ejecucion="NO_REALIZADO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
            ejecutado_at=datetime(2026, 8, 15, 10, 0, 0),
            ejecutado_por_user_id=u.id,
        )
        db.session.add(item2)
        db.session.flush()

        nr = build_indicadores_no_realizadas(_DESDE, _HASTA)
        general_clima = next(
            r.cantidad for r in nr.contraproducencias_resumen if r.bucket == "clima"
        )
        assert general_clima >= 2

        prod = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, prod.inspectores_no_realizadas)
        assert row is not None
        assert row.clima == 2
        assert row.clima <= general_clima
        _assert_bucket_invariant(_DESDE, _HASTA)
        assert item1.id != item2.id
    finally:
        db.session.rollback()


def test_periodo_vacio_arrays(app_ctx) -> None:
    try:
        out = build_indicadores_productividad(date(2099, 1, 1), date(2099, 1, 31))
        assert out.inspectores_realizadas == []
        assert out.inspectores_no_realizadas == []
        assert out.actas_por_inspector == []
    finally:
        db.session.rollback()


def test_get_api_productividad_200(client, auth_headers) -> None:
    resp = client.get(
        "/api/indicadores/productividad?desde=2026-08-01&hasta=2026-08-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in ("inspectores_realizadas", "inspectores_no_realizadas", "actas_por_inspector"):
        assert key in data
        assert isinstance(data[key], list)


def test_resumen_sigue_funcionando(app_ctx) -> None:
    try:
        build_indicadores_resumen(date(2026, 1, 1), date(2026, 12, 31))
    finally:
        db.session.rollback()
