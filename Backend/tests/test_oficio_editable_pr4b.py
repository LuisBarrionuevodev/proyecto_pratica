"""PR4b — Política editable por oficio y bandeja reinspección por oficio/iniciador."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.domains.actuaciones.services.oficio_editable_service import evaluar_editable_oficio
from app.domains.actuaciones.services.oficio_list_service import oficios_comprobacion_payload
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Oficio,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"u_ed4b_{_unique_num()}",
        email=f"ed4b_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _circuito_con_envio() -> tuple[Actuaciones, JuzgadoCatalogo]:
    jz = JuzgadoCatalogo(codigo=f"JZED{_unique_num()}"[:32], nombre=f"Juzgado editable {_unique_num()}")
    db.session.add(jz)
    db.session.flush()
    dom = Domicilio(calle=f"CEd{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="ed4b")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 10),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.add(
        Expediente(
            numero_expediente=_unique_num()[:6],
            anio="2026",
            fecha_expediente=date(2026, 3, 12),
            tipo_expediente="ENVIO_ACTA",
            comprobacion_id=comp.id,
        )
    )
    db.session.flush()
    return act, jz


def _payload_oficio(juzgado_id: int, *, numero: str, fecha: date, num_exp: str) -> dict:
    return {
        "numero_oficio": numero,
        "fecha_oficio": fecha,
        "juzgado_id": juzgado_id,
        "numero_expediente_oficio": num_exp,
        "fecha_expediente_oficio": fecha,
    }


def test_oficio_sin_ruta_es_editable(app_ctx) -> None:
    act, jz = _circuito_con_envio()
    db.session.commit()
    r = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=f"O{_unique_num()[:4]}", fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    policy = evaluar_editable_oficio(r["oficio"].id)
    assert policy["editable"] is True
    payload = oficios_comprobacion_payload(int(act.comprobacion_id))[0]
    assert payload["editable"] is True


def test_oficio_en_ruta_publicada_no_editable(app_ctx) -> None:
    act, jz = _circuito_con_envio()
    u = _mk_user()
    db.session.commit()
    r = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=f"O{_unique_num()[:4]}", fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    ini = r["iniciador_ruta"]
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 15),
        turno="TARDE",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.add(
        RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=act.orden_trabajo_id,
            estado_ruta_item="PENDIENTE_ASIGNACION",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
    )
    db.session.commit()

    policy = evaluar_editable_oficio(r["oficio"].id)
    assert policy["editable"] is False
    assert policy["bloqueado_motivo"]
    assert policy["ruta_estado"] == "PUBLICADA"


def test_dos_oficios_dos_filas_bandeja_si_uno_en_ruta(app_ctx) -> None:
    act, jz = _circuito_con_envio()
    u = _mk_user()
    db.session.commit()
    num1, num2 = f"A{_unique_num()[:3]}", f"B{_unique_num()[:3]}"
    r1 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num1, fecha=date(2026, 4, 1), num_exp=_unique_num()[:6]),
    )
    r2 = complete_oficio_from_actuacion(
        act.id,
        _payload_oficio(jz.id, numero=num2, fecha=date(2026, 5, 2), num_exp=_unique_num()[:6]),
    )
    ruta = RutaTrabajo(
        fecha=date(2026, 6, 15),
        turno="TARDE",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    db.session.add(
        RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=r1["iniciador_ruta"].id,
            orden_trabajo_id=act.orden_trabajo_id,
            estado_ruta_item="PENDIENTE_ASIGNACION",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
    )
    db.session.commit()

    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters(omitir_rango_fecha=True)
    )
    oficios_en_bandeja = {f[1].numero_oficio for f in filas if f[0].id == act.id}
    assert oficios_en_bandeja == {num2}
    assert r1["oficio"].numero_oficio not in oficios_en_bandeja
