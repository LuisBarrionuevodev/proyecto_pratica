"""PR11.1e — IntegrityError orden_trabajo_id al republicar tras NO_REALIZADO (caso QA real)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    resolver_actuacion_para_publicar_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Actuaciones, IniciadorRuta, Inspector, OrdenTrabajo, Rubro, RutaItem, RutaTrabajo

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _dos_inspectores,
    _setup_borrador_con_iniciador,
    _unique_num,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1b import _mk_iniciador_relevamiento


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _cerrar_local_cerrado(item_id: int, user_id: int) -> None:
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
            ),
            ejecutado_por_user_id=user_id,
        )


def _insertar_segunda_actuacion_legacy_dual(
    *,
    ini: IniciadorRuta,
    act1_id: int,
    ot1_id: int,
    ot2_num: str,
    hoy: date,
    user_id: int,
) -> tuple[int, int]:
    """
    Simula estado legacy con dos actuaciones del mismo iniciador (INSERT duplicado histórico).

    Deja act1 con OT1 y crea act2 con OT2 vinculada a un ítem FINALIZADO/NO_REALIZADO.
    """
    import random

    act1 = Actuaciones.query.get(act1_id)
    assert act1 is not None
    act1.orden_trabajo_id = ot1_id

    ot2_row = OrdenTrabajo(numero_acta=ot2_num, anio=hoy.year, mes=hoy.month)
    db.session.add(ot2_row)
    db.session.flush()

    act2 = Actuaciones(
        fecha=hoy,
        mes=hoy.month,
        anio=hoy.year,
        tipo="INSPECCION",
        contraproducencia="LOCAL CERRADO",
        orden_trabajo_id=ot2_row.id,
        domicilio_id=ini.domicilio_id,
    )
    db.session.add(act2)
    db.session.flush()

    ins1, ins2 = _dos_inspectores()
    ruta_hist = RutaTrabajo(
        fecha=hoy,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=user_id,
    )
    db.session.add(ruta_hist)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta_hist.id, nombre="Hist PR11.1f", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta_hist.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    item_hist = RutaItem(
        ruta_trabajo_id=ruta_hist.id,
        ruta_grupo_id=grupo.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot2_row.id,
        actuacion_id=act2.id,
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="NO_REALIZADO",
        created_by_user_id=user_id,
    )
    db.session.add(item_hist)
    ruta_hist.estado_ruta = "PUBLICADA"
    db.session.commit()
    return int(act2.id), int(ot2_row.id)


def test_pr11_1e_republicar_misma_ot_no_integrity_error_caso_qa(app_ctx) -> None:
    """
    Caso QA: actuación previa ya tiene la OT objetivo; no debe INSERT duplicado.

    Simula IntegrityError ix_actuaciones_orden_trabajo_id al intentar CREATE en lugar
    de reutilizar la actuación del intento NO_REALIZADO.
    """
    ini = _mk_iniciador_relevamiento()
    from app.models import User

    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    hoy = date.today()
    ot_num = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None and item1_db.actuacion_id is not None
    act_id = int(item1_db.actuacion_id)
    ot_id = int(item1_db.orden_trabajo_id)

    _cerrar_local_cerrado(item1_db.id, u.id)
    db.session.expire_all()

    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    assert act_db.orden_trabajo_id == ot_id

    resolved = resolver_actuacion_para_publicar_item(
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot_id,
    )
    assert resolved is not None
    assert resolved.id == act_id

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_id
    assert (
        Actuaciones.query.filter(Actuaciones.orden_trabajo_id == ot_id).count() == 1
    )


def test_pr11_1e_resolver_prefiere_actuacion_con_ot_objetivo(app_ctx) -> None:
    """Si hay dos actuaciones del iniciador, usa la que ya tiene la OT nueva."""
    rub = Rubro.query.first()
    ins = Inspector.query.first()
    assert rub and ins
    from app.models import User

    u = User(
        username=f"u_pr11e_{uuid4().hex[:8]}",
        email=f"pr11e_{uuid4().hex[:8]}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()

    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-10",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": f"Pr11e_{uuid4().hex[:6]}", "numero": "1"},
            "rubro_nombre": rub.nombre,
        }
    )
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id).first()
    assert ini is not None
    db.session.commit()

    hoy = date.today()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    act1_id = int(item1_db.actuacion_id)
    ot1_id = int(item1_db.orden_trabajo_id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    act2_id, ot2_id = _insertar_segunda_actuacion_legacy_dual(
        ini=ini,
        act1_id=act1_id,
        ot1_id=ot1_id,
        ot2_num=ot2,
        hoy=hoy,
        user_id=u.id,
    )

    resolved = resolver_actuacion_para_publicar_item(
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot2_id,
    )
    assert resolved is not None
    assert resolved.id == act2_id

    ruta3, item3 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta3.id)
    db.session.expire_all()
    item3_db = RutaItem.query.get(item3.id)
    assert item3_db is not None
    assert item3_db.actuacion_id == act2_id
