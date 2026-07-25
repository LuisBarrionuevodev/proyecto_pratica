"""PR11.1d — Trazabilidad diagnóstica al publicar (sin cambiar reglas de negocio)."""

from __future__ import annotations

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    validar_orden_trabajo_disponible_para_publicar,
)
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
    RutaPublicarDebugError,
    parse_integrity_error,
    publicar_debug_habilitado,
)
from app.models import IniciadorRuta, RutaItem, RutaTrabajo

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _dos_inspectores,
    _mk_iniciador_reinspeccion_notificacion,
    _setup_borrador_con_iniciador,
    _unique_num,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_pr11_1d_debug_habilitado_por_defecto() -> None:
    assert publicar_debug_habilitado() is True


def test_pr11_1d_conflicto_ot_incluye_debug(app_ctx) -> None:
    ini1, _act_base, _noti, _u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini1, numero_ot=ot_num)
    from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo

    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None

    ini2, _, _, _ = _mk_iniciador_reinspeccion_notificacion()
    ruta2 = RutaTrabajo(
        fecha=ruta1.fecha,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=999,
        created_by_user_id=1,
    )
    db.session.add(ruta2)
    db.session.flush()
    from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
    from app.domains.rutas_trabajo.services.grupo_inspectores_service import (
        replace_grupo_inspectores,
    )
    from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
    from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
        set_orden_trabajo_on_item,
    )

    ins1, ins2 = _dos_inspectores()
    grupo = create_ruta_grupo(ruta_id=ruta2.id, nombre="G", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta2.id, grupo_id=grupo.id, inspector_ids=[ins1.id, ins2.id]
    )
    items2 = assign_iniciadores_to_grupo(
        ruta_id=ruta2.id, grupo_id=grupo.id, iniciador_ids=[ini2.id]
    )
    item2 = items2[0]
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    item2_db.orden_trabajo_id = item1_db.orden_trabajo_id
    db.session.commit()

    ini2_db = IniciadorRuta.query.get(ini2.id)
    assert ini2_db is not None
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        validar_orden_trabajo_disponible_para_publicar(
            orden_trabajo_id=int(item1_db.orden_trabajo_id),
            ruta_item_id=item2_db.id,
            iniciador=ini2_db,
            ruta=ruta2,
            item=item2_db,
        )
    debug = exc_info.value.debug
    assert debug.get("validator") == "buscar_conflicto_orden_trabajo_al_publicar"
    assert debug.get("actuacion_bloqueante_id") is not None
    assert debug.get("item_bloqueante_id") is not None


def test_pr11_1d_parse_integrity_error_uq_notificacion() -> None:
    class _Orig:
        args = (1062,)

    exc = type("IntegrityError", (Exception,), {})()
    exc.orig = _Orig()
    exc.__str__ = lambda self: (  # type: ignore[method-assign]
        "Duplicate entry '2026-REINSPECCION-99' for key 'uq_act_anio_tipo_notificacion'"
    )
    info = parse_integrity_error(exc)  # type: ignore[arg-type]
    assert info["constraint_name"] == "uq_act_anio_tipo_notificacion"
    assert "notificacion" in str(info.get("columns_probables", []))
