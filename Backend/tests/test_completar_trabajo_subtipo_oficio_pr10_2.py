"""PR10.2 — Subtipo oficio conservado tras contraproducencia y segundo intento exitoso."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.list_item import actuacion_to_list_item
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    CatalogContraproducencia,
    IniciadorRuta,
    Inspector,
    RutaItem,
    RutaTrabajo,
)

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspector_ids() -> list[int]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return [int(rows[0].id), int(rows[1].id)]


def _republicar_iniciador_pendiente(
    ini: IniciadorRuta,
    user_id: int,
    *,
    fecha: date | None = None,
) -> RutaItem:
    """
    Asigna un iniciador PENDIENTE a una ruta BORRADOR nueva y la publica.

    Retorno:
        RutaItem EN_PROCESO con actuación mínima creada al publicar.
    """
    assert ini.estado_iniciador == "PENDIENTE"
    f = fecha or date(2026, 6, 18)
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        created_by_user_id=user_id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()

    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre=f"G_{uuid4().hex[:6]}", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=_dos_inspector_ids(),
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=_unique_num(),
    )
    db.session.commit()

    ruta_id = int(ruta.id)
    publicar_ruta_trabajo(ruta_id=ruta_id)
    db.session.expunge_all()
    refreshed = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta_id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert refreshed is not None
    return refreshed


def _cerrar_segundo_intento_realizado(
    item: RutaItem,
    user_id: int,
    *,
    tipo_iniciador: str,
) -> Actuaciones:
    """Cierra el segundo intento según el modo del iniciador promovido."""
    from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
        tipo_actuacion_fijo_para_iniciador_oficio,
    )

    if tipo_iniciador in ("RATIFICACION_CLAUSURA_OFICIO", "RATIFICACION_DECOMISO_OFICIO"):
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": tipo_actuacion_fijo_para_iniciador_oficio(tipo_iniciador),
                "resultado_cumplimiento_oficio": "CUMPLE",
            }
        )
    elif tipo_iniciador == "REINSPECCION_OFICIO":
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": _unique_num(),
            }
        )
    elif tipo_iniciador == "VERIFICAR_INFORMAR_OFICIO":
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": _unique_num(),
            }
        )
    else:
        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {"acta_inspeccion_num": _unique_num()}
        )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None and item_db.actuacion_id is not None
    act = db.session.get(Actuaciones, item_db.actuacion_id)
    assert act is not None
    return act


@pytest.mark.parametrize(
    ("primer_cierre", "tipo_esperado", "tipo_iniciador_esperado"),
    [
        (
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "VERIFICAR E INFORMAR"},
            "VERIFICAR E INFORMAR",
            "VERIFICAR_INFORMAR_OFICIO",
        ),
        (
            {"contraproducencia": "NO SE RATIFICÓ", "tipo_actuacion": "RATIFICACION DE CLAUSURA"},
            "RATIFICACION DE CLAUSURA",
            "RATIFICACION_CLAUSURA_OFICIO",
        ),
        (
            {
                "contraproducencia": "NO PAGÓ TODAVÍA EL DECOMISO",
                "tipo_actuacion": "RATIFICACION DE DECOMISO",
            },
            "RATIFICACION DE DECOMISO",
            "RATIFICACION_DECOMISO_OFICIO",
        ),
    ],
)
def test_subtipo_oficio_conservado_tras_contraproducencia_y_segundo_intento(
    app_ctx,
    primer_cierre: dict[str, str],
    tipo_esperado: str,
    tipo_iniciador_esperado: str,
) -> None:
    """
    Intento 1 no realizado + subtipo elegido → iniciador promovido → republicación y cierre
    conservan el tipo visible en Actuaciones.
    """
    for nombre in (
        primer_cierre.get("contraproducencia"),
        "NO SE RATIFICÓ",
        "NO PAGÓ TODAVÍA EL DECOMISO",
    ):
        if nombre:
            _ensure_catalog_contraproducencia(nombre)

    suf = uuid4().hex[:8]
    item, _act1, ini, u = _mk_reinspeccion_oficio_item(suf)
    user_id = int(u.id)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(primer_cierre),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"
    assert ini_db.tipo_iniciador == tipo_iniciador_esperado

    item2 = _republicar_iniciador_pendiente(ini_db, user_id)
    act_pub = db.session.get(Actuaciones, item2.actuacion_id)
    assert act_pub is not None
    assert str(act_pub.tipo) == tipo_esperado

    act_final = _cerrar_segundo_intento_realizado(
        item2,
        user_id,
        tipo_iniciador=tipo_iniciador_esperado,
    )
    assert str(act_final.tipo) == tipo_esperado

    list_row = actuacion_to_list_item(act_final)
    assert list_row["tipo_actuacion"] == tipo_esperado


def test_ratificacion_clausura_promovida_cierra_con_cumplimiento(app_ctx) -> None:
    """Iniciador promovido acepta cierre por cumplimiento sin acta de inspección."""
    from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item

    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert act_db is not None
    assert str(act_db.tipo) == "RATIFICACION DE CLAUSURA"
    assert act_db.resultado_cumplimiento_oficio == "CUMPLE"
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"


def test_verificar_informar_promovido_cierra_sin_nueva_inspeccion(app_ctx) -> None:
    """Verificar e informar sin nueva inspección: cierra sin actas normales."""
    from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item

    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    ini.tipo_iniciador = "VERIFICAR_INFORMAR_OFICIO"
    db.session.commit()

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
            "observaciones_ejecucion": "Sin inspección en esta visita",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, act.id)
    assert act_db is not None
    assert str(act_db.tipo) == "VERIFICAR E INFORMAR"
    assert act_db.inspeccion is None


def test_verificar_informar_rechaza_actas_si_sin_nueva_inspeccion(app_ctx) -> None:
    from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item

    suf = uuid4().hex[:8]
    item, _act, ini, u = _mk_reinspeccion_oficio_item(suf)
    ini.tipo_iniciador = "VERIFICAR_INFORMAR_OFICIO"
    db.session.commit()

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
            "acta_inspeccion_num": _unique_num(),
        }
    )
    with pytest.raises(ValueError, match="sin nueva inspección"):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=int(u.id),
        )


def test_reinspeccion_notificacion_sigue_como_reinspeccion(app_ctx) -> None:
    """Reinspección por notificación no debe adoptar subtipos de oficio."""
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    user_id = int(u.id)

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None
    assert ini_db.tipo_iniciador == "REINSPECCION_NOTIFICACION"

    ini_db.estado_iniciador = "PENDIENTE"
    db.session.commit()

    item2 = _republicar_iniciador_pendiente(ini_db, user_id)
    act_final = _cerrar_segundo_intento_realizado(
        item2,
        user_id,
        tipo_iniciador="REINSPECCION_NOTIFICACION",
    )
    assert str(act_final.tipo) == "REINSPECCION"
    list_row = actuacion_to_list_item(act_final)
    assert list_row["tipo_actuacion"] == "REINSPECCION"
