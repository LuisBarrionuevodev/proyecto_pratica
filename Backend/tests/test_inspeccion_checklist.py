"""INSPECCIÓN-CHECKLIST.2 — estados BIEN/OBSERVADO + personas sin carnet."""

from __future__ import annotations

import random

import pytest
import sqlalchemy as sa
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.attach.inspeccion import (
    aplicar_inspeccion_checklist_desde_payload,
    items_acta_inspeccion_read_dtos,
)
from app.domains.catalogos.services.item_acta_inspeccion_catalog_service import (
    listar_items_acta_inspeccion_catalogo,
)
from app.domains.actuaciones.attach.notificacion import aplicar_personas_sin_carnet_desde_payload
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import ActaInspeccionItem, Inspeccion, ItemActaInspeccion, Motivo, Notificacion, Rubro
from app.models.inspector import Inspector


def _unique_ot() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_acta() -> str:
    return f"{random.randint(0, 999999):06d}"


def _resolve_inspector_nombre() -> str:
    row = Inspector.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un inspector en la BD de test")
    return str(row.nombre)


def _resolve_rubro_nombre() -> str:
    row = Rubro.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un rubro en la BD de test")
    return str(row.nombre)


def _resolve_motivo_nombre() -> str:
    row = Motivo.query.first()
    if row is None:
        pytest.skip("Se requiere al menos un motivo en catálogo")
    return str(row.nombre)


_CANONICAL_ITEMS = [
    ("TIENE_BANO", "Baño", 1, "ESTADO"),
    ("TIENE_SALON", "Salón", 2, "ESTADO"),
    ("TIENE_DEPOSITO", "Depósito", 3, "ESTADO"),
    ("TIENE_COCINA_MESA_TRABAJO", "Cocina / mesa de trabajo", 4, "ESTADO"),
    ("VAJILLA_MANTEL", "Vajilla / mantel", 5, "ESTADO"),
    ("TIENE_HABILITACION", "Tiene habilitación", 6, "SI_NO"),
]


@pytest.fixture()
def items_catalogo(app):
    with app.app_context():
        rows = ItemActaInspeccion.query.order_by(ItemActaInspeccion.orden.asc()).all()
        if not rows:
            seeds = [
                ItemActaInspeccion(
                    codigo="TIENE_BANO",
                    nombre="Baño",
                    activo=True,
                    orden=1,
                    tipo_respuesta="ESTADO",
                ),
                ItemActaInspeccion(
                    codigo="TIENE_SALON",
                    nombre="Salón",
                    activo=True,
                    orden=2,
                    tipo_respuesta="ESTADO",
                ),
                ItemActaInspeccion(
                    codigo="TIENE_DEPOSITO",
                    nombre="Depósito",
                    activo=True,
                    orden=3,
                    tipo_respuesta="ESTADO",
                ),
                ItemActaInspeccion(
                    codigo="TIENE_COCINA_MESA_TRABAJO",
                    nombre="Cocina / mesa de trabajo",
                    activo=True,
                    orden=4,
                    tipo_respuesta="ESTADO",
                ),
                ItemActaInspeccion(
                    codigo="VAJILLA_MANTEL",
                    nombre="Vajilla / mantel",
                    activo=True,
                    orden=5,
                    tipo_respuesta="ESTADO",
                ),
                ItemActaInspeccion(
                    codigo="TIENE_HABILITACION",
                    nombre="Tiene habilitación",
                    activo=True,
                    orden=6,
                    tipo_respuesta="SI_NO",
                ),
            ]
            db.session.add_all(seeds)
            db.session.commit()
        else:
            for codigo, nombre, orden, tipo in _CANONICAL_ITEMS:
                row = ItemActaInspeccion.query.filter_by(codigo=codigo).first()
                if row is None:
                    db.session.add(
                        ItemActaInspeccion(
                            codigo=codigo,
                            nombre=nombre,
                            activo=True,
                            orden=orden,
                            tipo_respuesta=tipo,
                        )
                    )
                else:
                    row.nombre = nombre
                    row.orden = orden
                    row.activo = True
                    row.tipo_respuesta = tipo
                    db.session.add(row)
            db.session.commit()
        rows = ItemActaInspeccion.query.order_by(ItemActaInspeccion.orden.asc()).all()
        yield rows


def _item_id(items: list[ItemActaInspeccion], codigo: str) -> int:
    for row in items:
        if row.codigo == codigo:
            return int(row.id)
    raise AssertionError(f"Ítem {codigo} no encontrado en catálogo")


def _base_create_payload(**extra) -> dict:
    payload = {
        "orden_trabajo_numero": _unique_ot(),
        "fecha_actuacion": "2026-09-09",
        "tipo_actuacion": "INSPECCION",
        "contraproducencia": "NO_HUBO",
        "inspectores": [_resolve_inspector_nombre()],
        "domicilio": {"calle": "Calle Test", "numero": "123"},
        "rubro_nombre": _resolve_rubro_nombre(),
        "contribuyente": {
            "doc_nro": "30123456",
            "apellido": "Pérez",
            "nombre": "Juan",
        },
        "acta_inspeccion_num": _unique_acta(),
    }
    payload.update(extra)
    return payload


def _legacy_put_row_dict(act, **extra) -> dict:
    inspectores = [str(i.nombre) for i in (act.inspector or []) if getattr(i, "nombre", None)]
    if not inspectores:
        inspectores = [_resolve_inspector_nombre()]
    ot = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    row = {
        "id": act.id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": act.fecha.isoformat(),
        "rubro_nombre": _resolve_rubro_nombre(),
        "tipo_actuacion": act.tipo,
        "inspectores": inspectores,
    }
    row.update(extra)
    return row


def _put_actuacion(act, **row_extra) -> None:
    row = ActuacionGridRowIn.model_validate(_legacy_put_row_dict(act, **row_extra))
    actualizar_actuacion(int(act.id), map_actuacion_row(row))


def _count_junction(inspeccion_id: int) -> int:
    return int(
        db.session.execute(
            sa.text("SELECT COUNT(*) FROM acta_inspeccion_item WHERE acta_inspeccion_id = :iid"),
            {"iid": int(inspeccion_id)},
        ).scalar_one()
    )


def _junction_estados(inspeccion_id: int) -> dict[int, str]:
    rows = (
        db.session.query(ActaInspeccionItem)
        .filter(ActaInspeccionItem.acta_inspeccion_id == int(inspeccion_id))
        .all()
    )
    return {int(r.item_acta_inspeccion_id): str(r.estado) for r in rows}


def _junction_respuestas(inspeccion_id: int) -> dict[int, dict]:
    rows = (
        db.session.query(ActaInspeccionItem)
        .filter(ActaInspeccionItem.acta_inspeccion_id == int(inspeccion_id))
        .all()
    )
    return {
        int(r.item_acta_inspeccion_id): {
            "estado": r.estado,
            "valor_si_no": r.valor_si_no,
        }
        for r in rows
    }


def test_create_con_estados_bien_observado(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        id_deposito = _item_id(items_catalogo, "TIENE_DEPOSITO")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[
                    {"item_id": id_bano, "estado": "BIEN"},
                    {"item_id": id_deposito, "estado": "OBSERVADO"},
                ]
            )
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert ins is not None
        estados = _junction_estados(int(ins.id))
        assert estados == {id_bano: "BIEN", id_deposito: "OBSERVADO"}


def test_legacy_put_preserva_estados(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        id_deposito = _item_id(items_catalogo, "TIENE_DEPOSITO")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[
                    {"item_id": id_bano, "estado": "BIEN"},
                    {"item_id": id_deposito, "estado": "OBSERVADO"},
                ]
            )
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert _count_junction(int(ins.id)) == 2

        _put_actuacion(act)
        ins2 = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert _junction_estados(int(ins2.id)) == {id_bano: "BIEN", id_deposito: "OBSERVADO"}


def test_explicit_clear_items(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        act = crear_actuacion_desde_payload(
            _base_create_payload(items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}])
        )
        _put_actuacion(act, items_acta_inspeccion=[])
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert _count_junction(int(ins.id)) == 0


def test_cambio_estado_bien_a_observado(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        act = crear_actuacion_desde_payload(
            _base_create_payload(items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}])
        )
        _put_actuacion(act, items_acta_inspeccion=[{"item_id": id_bano, "estado": "OBSERVADO"}])
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert _junction_estados(int(ins.id)) == {id_bano: "OBSERVADO"}
        assert _count_junction(int(ins.id)) == 1


def test_replace_items(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        id_deposito = _item_id(items_catalogo, "TIENE_DEPOSITO")
        id_salon = _item_id(items_catalogo, "TIENE_SALON")
        id_vajilla = _item_id(items_catalogo, "VAJILLA_MANTEL")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[
                    {"item_id": id_bano, "estado": "BIEN"},
                    {"item_id": id_deposito, "estado": "OBSERVADO"},
                ]
            )
        )
        replace = [
            {"item_id": id_salon, "estado": "BIEN"},
            {"item_id": id_vajilla, "estado": "OBSERVADO"},
        ]
        _put_actuacion(act, items_acta_inspeccion=replace)
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert _junction_estados(int(ins.id)) == {
            id_salon: "BIEN",
            id_vajilla: "OBSERVADO",
        }
        _put_actuacion(act, items_acta_inspeccion=replace)
        assert _count_junction(int(ins.id)) == 2


def test_rechaza_contrato_v1_ids(app):
    with pytest.raises(ValidationError, match="items_acta_inspeccion_ids"):
        ActuacionGridRowIn.model_validate(
            {
                "orden_trabajo_numero": "000001",
                "fecha_actuacion": "2026-09-09",
                "items_acta_inspeccion_ids": [1],
            }
        )


def test_personas_sin_carnet_preserve_cero_valor(app, items_catalogo):
    with app.app_context():
        motivo = _resolve_motivo_nombre()
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                notificacion={"acta_num": _unique_acta(), "motivos": [motivo]},
                cantidad_personas_sin_carnet_sanidad=4,
            )
        )
        _put_actuacion(act)
        noti = db.session.get(Notificacion, int(act.notificacion_id))
        assert int(noti.cantidad_personas_sin_carnet_sanidad) == 4

        _put_actuacion(act, cantidad_personas_sin_carnet_sanidad=0)
        noti = db.session.get(Notificacion, int(act.notificacion_id))
        assert int(noti.cantidad_personas_sin_carnet_sanidad) == 0

        _put_actuacion(act, cantidad_personas_sin_carnet_sanidad=2)
        noti = db.session.get(Notificacion, int(act.notificacion_id))
        assert int(noti.cantidad_personas_sin_carnet_sanidad) == 2


def test_personas_sin_carnet_negativo_rechazado(app, items_catalogo):
    with pytest.raises(ValidationError):
        ActuacionGridRowIn.model_validate(
            {
                "orden_trabajo_numero": "000001",
                "fecha_actuacion": "2026-09-09",
                "cantidad_personas_sin_carnet_sanidad": -1,
            }
        )


def test_personas_sin_carnet_null_rechazado(app, items_catalogo):
    with app.app_context():
        act = crear_actuacion_desde_payload(_base_create_payload())
        with pytest.raises(ValueError, match="no puede ser nula"):
            aplicar_personas_sin_carnet_desde_payload(
                act, {"cantidad_personas_sin_carnet_sanidad": None}
            )


def test_personas_sin_carnet_sin_notificacion_falla(app, items_catalogo):
    with app.app_context():
        act = crear_actuacion_desde_payload(_base_create_payload())
        with pytest.raises(ValueError, match="acta de notificación"):
            aplicar_personas_sin_carnet_desde_payload(
                act, {"cantidad_personas_sin_carnet_sanidad": 3}
            )


def test_checklist_sin_inspeccion_falla(app, items_catalogo):
    with app.app_context():
        act = crear_actuacion_desde_payload(
            {
                "orden_trabajo_numero": _unique_ot(),
                "fecha_actuacion": "2026-09-09",
                "tipo_actuacion": "INSPECCION",
                "contraproducencia": "NO_HUBO",
                "inspectores": [_resolve_inspector_nombre()],
                "domicilio": {"calle": "Calle Test", "numero": "123"},
                "rubro_nombre": _resolve_rubro_nombre(),
                "contribuyente": {
                    "doc_nro": "30999888",
                    "apellido": "López",
                    "nombre": "Ana",
                },
            }
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        if ins:
            db.session.delete(ins)
            db.session.commit()
        with pytest.raises(ValueError, match="No hay acta de inspección"):
            aplicar_inspeccion_checklist_desde_payload(
                act,
                {"items_acta_inspeccion": [{"item_id": _item_id(items_catalogo, "TIENE_BANO"), "estado": "BIEN"}]},
            )


def test_create_legacy_sin_checklist(app, items_catalogo):
    with app.app_context():
        act = crear_actuacion_desde_payload(_base_create_payload())
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        assert ins is not None
        assert _count_junction(int(ins.id)) == 0


def test_quitar_acta_elimina_junctions(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        act = crear_actuacion_desde_payload(
            _base_create_payload(items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}])
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        ins_id = int(ins.id)
        quitar_acta_canal_actas(int(act.id), "INSPECCION")
        assert Inspeccion.query.get(ins_id) is None
        assert _count_junction(ins_id) == 0


def test_quitar_notificacion_elimina_personas_sin_carnet(app, items_catalogo):
    with app.app_context():
        motivo = _resolve_motivo_nombre()
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                notificacion={"acta_num": _unique_acta(), "motivos": [motivo]},
                cantidad_personas_sin_carnet_sanidad=4,
            )
        )
        noti_id = int(act.notificacion_id)
        quitar_acta_canal_actas(int(act.id), "NOTIFICACION")
        act2 = db.session.get(type(act), int(act.id))
        assert act2.notificacion_id is None
        noti = db.session.get(Notificacion, noti_id)
        assert noti is not None
        assert noti.deleted_at is not None
        assert int(noti.cantidad_personas_sin_carnet_sanidad) == 4


def test_migration_v2_schema(app):
    """b1c2d3e4f5a6 aplicada: estado junction, seed Vajilla, columna Notificación."""
    with app.app_context():
        bind = db.engine
        insp = sa.inspect(bind)
        junction_cols = {c["name"] for c in insp.get_columns("acta_inspeccion_item")}
        assert "estado" in junction_cols
        assert "cantidad_carnets_sanidad" not in {c["name"] for c in insp.get_columns("inspeccion")}
        noti_cols = {c["name"] for c in insp.get_columns("notificacion")}
        assert "cantidad_personas_sin_carnet_sanidad" in noti_cols

        vajilla = ItemActaInspeccion.query.filter_by(codigo="VAJILLA_MANTEL").first()
        assert vajilla is not None
        assert vajilla.nombre == "Vajilla / mantel"
        assert int(vajilla.orden) == 5

        bano = ItemActaInspeccion.query.filter_by(codigo="TIENE_BANO").first()
        assert bano is not None
        assert bano.nombre == "Baño"


def test_create_si_no_true_y_false(app, items_catalogo):
    with app.app_context():
        id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": True}]
            )
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        resp = _junction_respuestas(int(ins.id))
        assert resp[id_hab] == {"estado": None, "valor_si_no": True}

        _put_actuacion(act, items_acta_inspeccion=[{"item_id": id_hab, "valor_si_no": False}])
        ins2 = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        resp2 = _junction_respuestas(int(ins2.id))
        assert resp2[id_hab] == {"estado": None, "valor_si_no": False}


def test_sparse_sin_habilitacion(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[{"item_id": id_bano, "estado": "BIEN"}]
            )
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        resp = _junction_respuestas(int(ins.id))
        assert id_hab not in resp
        dtos = items_acta_inspeccion_read_dtos(ins)
        assert all(d["codigo"] != "TIENE_HABILITACION" for d in dtos)


def test_historico_sin_habilitacion_no_inferir_false(app, items_catalogo):
    with app.app_context():
        act = crear_actuacion_desde_payload(_base_create_payload())
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        dtos = items_acta_inspeccion_read_dtos(ins)
        hab = [d for d in dtos if d.get("codigo") == "TIENE_HABILITACION"]
        assert hab == []
        id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
        assert id_hab not in _junction_respuestas(int(ins.id))


def test_rechaza_si_no_con_estado(app, items_catalogo):
    with app.app_context():
        id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
        act = crear_actuacion_desde_payload(_base_create_payload())
        with pytest.raises(ValueError, match="valor_si_no"):
            aplicar_inspeccion_checklist_desde_payload(
                act,
                {
                    "items_acta_inspeccion": [
                        {"item_id": id_hab, "estado": "BIEN"},
                    ]
                },
            )


def test_rechaza_estado_con_valor_si_no(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        act = crear_actuacion_desde_payload(_base_create_payload())
        with pytest.raises(ValueError, match="valor_si_no"):
            aplicar_inspeccion_checklist_desde_payload(
                act,
                {
                    "items_acta_inspeccion": [
                        {"item_id": id_bano, "estado": "BIEN", "valor_si_no": True},
                    ]
                },
            )


def test_rechaza_estado_item_con_valor_si_no(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        act = crear_actuacion_desde_payload(_base_create_payload())
        with pytest.raises(ValueError, match="estado BIEN u OBSERVADO"):
            aplicar_inspeccion_checklist_desde_payload(
                act,
                {"items_acta_inspeccion": [{"item_id": id_bano, "valor_si_no": True}]},
            )


def test_rechaza_item_sin_respuesta(app, items_catalogo):
    with pytest.raises(ValidationError, match="estado"):
        ActuacionGridRowIn.model_validate(
            {
                "orden_trabajo_numero": "000001",
                "fecha_actuacion": "2026-09-09",
                "items_acta_inspeccion": [{"item_id": 1}],
            }
        )


def test_catalogo_incluye_tipo_respuesta(app, items_catalogo):
    with app.app_context():
        items = listar_items_acta_inspeccion_catalogo(solo_activos=True)
        hab = next(i for i in items if i["codigo"] == "TIENE_HABILITACION")
        assert hab["tipo_respuesta"] == "SI_NO"
        bano = next(i for i in items if i["codigo"] == "TIENE_BANO")
        assert bano["tipo_respuesta"] == "ESTADO"


def test_read_dto_tipado(app, items_catalogo):
    with app.app_context():
        id_bano = _item_id(items_catalogo, "TIENE_BANO")
        id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
        act = crear_actuacion_desde_payload(
            _base_create_payload(
                items_acta_inspeccion=[
                    {"item_id": id_bano, "estado": "OBSERVADO"},
                    {"item_id": id_hab, "valor_si_no": True},
                ]
            )
        )
        ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
        dtos = items_acta_inspeccion_read_dtos(ins)
        by_codigo = {d["codigo"]: d for d in dtos}
        assert by_codigo["TIENE_BANO"]["tipo_respuesta"] == "ESTADO"
        assert by_codigo["TIENE_BANO"]["estado"] == "OBSERVADO"
        assert by_codigo["TIENE_BANO"]["valor_si_no"] is None
        assert by_codigo["TIENE_HABILITACION"]["tipo_respuesta"] == "SI_NO"
        assert by_codigo["TIENE_HABILITACION"]["estado"] is None
        assert by_codigo["TIENE_HABILITACION"]["valor_si_no"] is True


def test_migration_tipo_si_no_schema(app):
    with app.app_context():
        bind = db.engine
        insp = sa.inspect(bind)
        catalog_cols = {c["name"] for c in insp.get_columns("item_acta_inspeccion")}
        junction_cols = {c["name"] for c in insp.get_columns("acta_inspeccion_item")}
        assert "tipo_respuesta" in catalog_cols
        assert "valor_si_no" in junction_cols

        hab = ItemActaInspeccion.query.filter_by(codigo="TIENE_HABILITACION").first()
        assert hab is not None
        assert hab.tipo_respuesta == "SI_NO"
