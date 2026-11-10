"""V1.1-COMP-MOTIVOS.2 — selección múltiple, lectura y legado.

No cubre oficios/expedientes más allá de no mutarlos. Rollback al final de cada test.
"""

from __future__ import annotations

import random
from datetime import date

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    referencia_actuacion_from_grid_row,
)
from app.domains.actuaciones.schemas.actuacion_inspector_patch_in import ActuacionInspectorPatchIn
from app.domains.actuaciones.schemas.comprobacion_motivos_in import parse_lista_motivos_comprobacion
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion
from app.domains.catalogos.canonical.motivos import MOTIVOS_COMPROBACION_CANONICOS
from app.models import (
    CatalogMotivoComprobacion,
    Comprobacion,
    Oficio,
)
from app.models.comprobacion import SEPARADOR_TEXTO_MOTIVOS_COMPROBACION
from tests.test_comp_motivos_1 import _ensure_catalogos, _mk_actuacion, _unique_acta


def _tres_catalogo() -> tuple[CatalogMotivoComprobacion, CatalogMotivoComprobacion, CatalogMotivoComprobacion]:
    rows = _ensure_catalogos()
    if len(rows) < 3:
        pytest.skip("Se requieren al menos tres motivos de comprobación en catálogo")
    by_name = {r.nombre: r for r in rows}
    nombres = list(MOTIVOS_COMPROBACION_CANONICOS)[:3]
    return by_name[nombres[0]], by_name[nombres[1]], by_name[nombres[2]]


def _nombres(comp: Comprobacion) -> list[str]:
    return [m.nombre for m in comp.motivos_comprobacion_ordenados()]


def test_crear_comprobacion_con_1_2_y_3_motivos(app_ctx) -> None:
    try:
        a, b, c = _tres_catalogo()
        for nombres in ([a.nombre], [a.nombre, b.nombre], [a.nombre, b.nombre, c.nombre]):
            act = _mk_actuacion()
            attach_comprobacion(
                act,
                {"acta_num": _unique_acta(), "motivos": nombres, "motivo": nombres[0]},
            )
            db.session.flush()
            comp = db.session.get(Comprobacion, act.comprobacion_id)
            assert comp is not None
            assert _nombres(comp) == nombres
            assert comp.motivo == SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(nombres)
            row = actuacion_to_grid_row(act)
            assert row["motivos_comprobacion"] == nombres
            assert row["motivos_comprobacion_texto"] == SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(
                nombres
            )
            assert row["comprobacion_motivo"] == SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(nombres)
    finally:
        db.session.rollback()


def test_quitar_motivo_del_medio_y_guardar(app_ctx) -> None:
    try:
        a, b, c = _tres_catalogo()
        act = _mk_actuacion()
        acta = _unique_acta()
        attach_comprobacion(act, {"acta_num": acta, "motivos": [a.nombre, b.nombre, c.nombre]})
        db.session.flush()
        attach_comprobacion(act, {"acta_num": acta, "motivos": [a.nombre, c.nombre]})
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert _nombres(comp) == [a.nombre, c.nombre]
        assert b.nombre not in _nombres(comp)
    finally:
        db.session.rollback()


def test_no_permite_duplicados_en_lista(app_ctx) -> None:
    cat = _ensure_catalogos()[0]
    with pytest.raises(ValueError, match="no puede repetirse"):
        parse_lista_motivos_comprobacion([cat.nombre, cat.nombre])


def test_rechaza_comprobacion_nueva_sin_motivos(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        with pytest.raises(ValueError, match="obligatorio"):
            attach_comprobacion(act, {"acta_num": _unique_acta(), "motivo": ""})
        with pytest.raises(ValueError, match="obligatorio"):
            attach_comprobacion(act, {"acta_num": _unique_acta(), "motivos": []})
    finally:
        db.session.rollback()


def test_historica_un_motivo_se_abre_sin_perderlo(app_ctx) -> None:
    try:
        a, _, _ = _tres_catalogo()
        act = _mk_actuacion()
        attach_comprobacion(act, {"acta_num": _unique_acta(), "motivo": a.nombre})
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["motivos_comprobacion"] == [a.nombre]
        attach_comprobacion(
            act,
            {
                "acta_num": row["acta_comprobacion_num"],
                "motivos": [a.nombre],
                "motivo": a.nombre,
            },
        )
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert _nombres(comp) == [a.nombre]
        assert comp.motivo == a.nombre
    finally:
        db.session.rollback()


def test_cambio_ajeno_no_reduce_lista_multiple(app_ctx) -> None:
    try:
        a, b, c = _tres_catalogo()
        act = _mk_actuacion()
        attach_comprobacion(
            act, {"acta_num": _unique_acta(), "motivos": [a.nombre, b.nombre, c.nombre]}
        )
        db.session.flush()
        aplicar_payload_actuacion(act, {"nombre_local": "Local sin tocar motivos"})
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert _nombres(comp) == [a.nombre, b.nombre, c.nombre]
    finally:
        db.session.rollback()


def test_payload_legado_no_reduce_varios_motivos(app_ctx) -> None:
    try:
        a, b, _ = _tres_catalogo()
        act = _mk_actuacion()
        acta = _unique_acta()
        attach_comprobacion(act, {"acta_num": acta, "motivos": [a.nombre, b.nombre]})
        db.session.flush()
        with pytest.raises(ValidationError) as exc:
            attach_comprobacion(act, {"acta_num": acta, "motivo": a.nombre})
        assert "varios motivos" in str(exc.value).lower()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        db.session.refresh(comp)
        assert _nombres(comp) == [a.nombre, b.nombre]
    finally:
        db.session.rollback()


def test_rechaza_motivo_inexistente(app_ctx) -> None:
    with pytest.raises(ValueError, match="catálogo"):
        parse_lista_motivos_comprobacion(["Motivo inventado CM2 xyz"])


def test_lectura_grid_y_referencia_muestran_todos(app_ctx) -> None:
    try:
        a, b, _ = _tres_catalogo()
        act = _mk_actuacion()
        attach_comprobacion(act, {"acta_num": _unique_acta(), "motivos": [b.nombre, a.nombre]})
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["motivos_comprobacion"] == [b.nombre, a.nombre]
        ref = referencia_actuacion_from_grid_row(row)
        assert ref["motivos_comprobacion"] == [b.nombre, a.nombre]
        assert ref["motivos_comprobacion_texto"] == SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(
            [b.nombre, a.nombre]
        )
    finally:
        db.session.rollback()


def test_inspector_patch_acepta_lista(app_ctx) -> None:
    a, b, _ = _tres_catalogo()
    patch = ActuacionInspectorPatchIn.model_validate(
        {
            "acta_comprobacion_num": "654321",
            "motivos_comprobacion": [a.nombre, b.nombre],
            "comprobacion_motivo": a.nombre,
        }
    )
    assert patch.motivos_comprobacion == [a.nombre, b.nombre]


def test_mapper_grid_envia_lista_completa(app_ctx) -> None:
    a, b, _ = _tres_catalogo()
    row = ActuacionGridRowIn.model_construct(
        _fields_set={
            "fecha_actuacion",
            "acta_comprobacion_num",
            "comprobacion_motivo",
            "motivos_comprobacion",
        },
        fecha_actuacion=date(2026, 11, 9),
        acta_comprobacion_num="111111",
        comprobacion_motivo=a.nombre,
        motivos_comprobacion=[a.nombre, b.nombre],
    )
    payload = map_actuacion_row(row)
    assert payload["comprobacion"]["motivos"] == [a.nombre, b.nombre]


def test_oficio_no_cambia_al_editar_motivos(app_ctx) -> None:
    try:
        a, b, _ = _tres_catalogo()
        act = _mk_actuacion()
        acta = _unique_acta()
        attach_comprobacion(act, {"acta_num": acta, "motivos": [a.nombre]})
        db.session.flush()
        ofi = Oficio(
            numero_oficio=f"OF{random.randint(100000, 999999)}",
            anio=2026,
            fecha_oficio=date(2026, 11, 9),
            causa="Test MOTIVOS.2",
            comprobacion_id=act.comprobacion_id,
            iniciador_materializacion_estado="MATERIALIZADO",
        )
        db.session.add(ofi)
        db.session.flush()
        ofi_id = int(ofi.id)
        estado_antes = ofi.iniciador_materializacion_estado
        causa_antes = ofi.causa
        attach_comprobacion(act, {"acta_num": acta, "motivos": [a.nombre, b.nombre]})
        db.session.flush()
        ofi2 = db.session.get(Oficio, ofi_id)
        assert ofi2 is not None
        assert ofi2.iniciador_materializacion_estado == estado_antes
        assert ofi2.causa == causa_antes
        assert ofi2.comprobacion_id == act.comprobacion_id
        assert ofi2.deleted_at is None
    finally:
        db.session.rollback()
