"""PR3 — Múltiples oficios por comprobación: backend."""

from __future__ import annotations

import random
from datetime import date, datetime, timezone

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import oficio_por_comprobacion
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.oficio_list_service import list_oficios_by_comprobacion
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_operativo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    DomicilioGeocode,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Oficio,
    OrdenTrabajo,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _actuacion_comprobacion_con_domicilio() -> tuple[Actuaciones, JuzgadoCatalogo]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="PR3Oficios", numero="10", distrito_id=None)
    db.session.add(dom)
    db.session.flush()
    geo = DomicilioGeocode(
        domicilio_id=dom.id,
        lat=-34.60,
        lng=-58.38,
        geo_status="OK",
    )
    db.session.add(geo)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="pr3 multiples oficios")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    j = JuzgadoCatalogo(codigo=f"j_{_unique_num()[:8]}", nombre=f"Juz {_unique_num()[:8]}")
    db.session.add(j)
    db.session.flush()
    return act, j


def _num_oficio() -> str:
    return f"OF{_unique_num()[:6]}"


def _payload_oficio(juzgado_id: int, *, numero: str, fecha: date, num_exp: str) -> dict:
    return {
        "numero_oficio": numero,
        "fecha_oficio": fecha,
        "juzgado_id": juzgado_id,
        "numero_expediente_oficio": num_exp,
        "fecha_expediente_oficio": fecha,
    }


def _setup_con_envio(act: Actuaciones) -> None:
    complete_expediente_from_actuacion(
        act.id,
        {"expediente_numero": _unique_num()[:6], "fecha_expediente": "2026-03-18"},
    )


def test_primer_oficio_ok(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    r = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=f"OF-{_unique_num()[:4]}", fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    assert r["oficio"].comprobacion_id == act.comprobacion_id
    assert r["expediente_respuesta_oficio"].oficio_id == r["oficio"].id
    assert r["iniciador_ruta"].oficio_id == r["oficio"].id


def test_segundo_oficio_distinto_ok_y_segundo_iniciador(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num1, num2 = _num_oficio(), _num_oficio()
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )

    assert r1["oficio"].id != r2["oficio"].id
    assert r1["iniciador_ruta"].id != r2["iniciador_ruta"].id
    assert r1["expediente_respuesta_oficio"].id != r2["expediente_respuesta_oficio"].id
    assert r2["expediente_respuesta_oficio"].oficio_id == r2["oficio"].id

    oficios = list_oficios_by_comprobacion(int(act.comprobacion_id))
    assert len(oficios) == 2


def test_oficio_duplicado_mismo_numero_anio_idempotente(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num = _num_oficio()
    payload = _payload_oficio(
        juz.id,
        numero=num,
        fecha=date(2026, 4, 1),
        num_exp=_unique_num()[:6],
    )
    r1 = complete_oficio_from_actuacion(act.id, payload)
    r2 = complete_oficio_from_actuacion(act.id, payload)

    assert r2["oficio"].id == r1["oficio"].id
    assert r2["expediente_respuesta_oficio"].id == r1["expediente_respuesta_oficio"].id
    assert r2["iniciador_ruta"].id == r1["iniciador_ruta"].id
    assert len(list_oficios_by_comprobacion(int(act.comprobacion_id))) == 1


def test_expediente_respuesta_duplicado_global_bloquea(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num_exp = _unique_num()[:6]
    complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=_num_oficio(), fecha=date(2026, 4, 1), num_exp=num_exp),
    )

    with pytest.raises(RuntimeError, match="ya existe"):
        complete_oficio_from_actuacion(
            act.id,
            _payload_oficio(juz.id, numero=_num_oficio(), fecha=date(2026, 5, 2), num_exp=num_exp),
        )


def test_reintento_iniciador_mismo_oficio_no_duplica(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    payload = _payload_oficio(
        juz.id,
        numero=f"OF-{_unique_num()[:4]}",
        fecha=date(2026, 4, 1),
        num_exp=_unique_num()[:6],
    )
    r1 = complete_oficio_from_actuacion(act.id, payload)
    r2 = complete_oficio_from_actuacion(act.id, payload)

    activos = (
        IniciadorRuta.query.filter(
            IniciadorRuta.oficio_id == r1["oficio"].id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .all()
    )
    assert len(activos) == 1
    assert r2["iniciador_ruta"].id == r1["iniciador_ruta"].id


def test_segundo_oficio_hereda_domicilio_operativo(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    esperado = resolve_domicilio_operativo_para_iniciador(int(act.domicilio_id))

    num1, num2 = _num_oficio(), _num_oficio()
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )

    assert r1["iniciador_ruta"].domicilio_id == esperado
    assert r2["iniciador_ruta"].domicilio_id == esperado


def test_list_oficios_by_comprobacion_devuelve_ambos(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num1, num2 = _num_oficio(), _num_oficio()
    complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )

    listed = list_oficios_by_comprobacion(int(act.comprobacion_id))
    assert len(listed) == 2
    assert {o.numero_oficio for o in listed} == {num1, num2}


def test_presenter_legacy_oficio_por_comprobacion_primer_oficio(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num1, num2 = _num_oficio(), _num_oficio()
    complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )

    legacy = oficio_por_comprobacion(int(act.comprobacion_id))
    assert legacy is not None
    assert legacy.numero_oficio == num1


def test_oficio_eliminado_no_bloquea_nuevo_distinto(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    num1, num2 = _num_oficio(), _num_oficio()
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    oficio = db.session.get(Oficio, r1["oficio"].id)
    assert oficio is not None
    oficio.deleted_at = datetime.now(timezone.utc)
    db.session.add(oficio)
    db.session.commit()

    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(juz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )
    assert r2["oficio"].numero_oficio == num2
    assert len(list_oficios_by_comprobacion(int(act.comprobacion_id))) == 1


def test_flujo_un_solo_oficio_existente_sigue_funcionando(app_ctx) -> None:
    """Compatibilidad: un oficio + reactivación soft-delete del expediente respuesta."""
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()
    _setup_con_envio(act)

    payload = _payload_oficio(
        juz.id,
        numero=f"OF-{_unique_num()[:4]}",
        fecha=date(2026, 4, 1),
        num_exp=_unique_num()[:6],
    )
    r1 = complete_oficio_from_actuacion(act.id, payload)
    ex = r1["expediente_respuesta_oficio"]
    ex.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex)
    db.session.commit()

    r2 = complete_oficio_from_actuacion(act.id, payload)
    assert r2["expediente_respuesta_oficio"].id == ex.id
    assert r2["expediente_respuesta_oficio"].deleted_at is None
