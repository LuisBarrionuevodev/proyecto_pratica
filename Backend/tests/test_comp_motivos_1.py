"""V1.1-COMP-MOTIVOS.1 — puente relacional y sync del motivo legado.

No cubre oficios ni reinspección. Requiere BD; rollback al final de cada test.
"""

from __future__ import annotations

import random
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.comprobacion_motivos_sync_service import (
    set_motivos_catalogo,
    sync_unico_vinculo_desde_texto_historico,
)
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.catalogos.canonical.motivos import MOTIVOS_COMPROBACION_CANONICOS
from app.models import (
    Actuaciones,
    CatalogMotivoComprobacion,
    Comprobacion,
    OrdenTrabajo,
)
from app.models.comprobacion import SEPARADOR_TEXTO_MOTIVOS_COMPROBACION
from app.models.comprobacion_motivo import comprobacion_motivo


def _unique_acta() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_actuacion() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_acta(), anio=2026, mes=11)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 11, 9),
        mes=11,
        anio=2026,
        orden_trabajo_id=ot.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _ensure_catalogos() -> list[CatalogMotivoComprobacion]:
    existentes = {str(r.nombre): r for r in CatalogMotivoComprobacion.query.all()}
    created = False
    for nombre in MOTIVOS_COMPROBACION_CANONICOS:
        if nombre not in existentes:
            row = CatalogMotivoComprobacion(nombre=nombre)
            db.session.add(row)
            existentes[nombre] = row
            created = True
    if created:
        db.session.flush()
    rows = list(existentes.values())
    rows.sort(key=lambda r: (r.nombre or "", int(r.id or 0)))
    return rows


def _catalogo_motivo() -> CatalogMotivoComprobacion:
    rows = _ensure_catalogos()
    return rows[0]


def _dos_catalogo() -> tuple[CatalogMotivoComprobacion, CatalogMotivoComprobacion]:
    rows = _ensure_catalogos()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos dos motivos de comprobación en catálogo")
    return rows[0], rows[1]


def _ids_vinculos(comp: Comprobacion) -> list[int]:
    return [int(m.id) for m in comp.motivos_comprobacion_ordenados()]


def test_historico_con_motivo_catalogo_crea_vinculo(app_ctx) -> None:
    try:
        cat = _catalogo_motivo()
        act = _mk_actuacion()
        attach_comprobacion(act, {"acta_num": _unique_acta(), "motivo": cat.nombre})
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert comp is not None
        assert comp.motivo == cat.nombre
        assert _ids_vinculos(comp) == [int(cat.id)]
        assert comp.motivos_comprobacion_as_dicts() == [{"id": int(cat.id), "nombre": cat.nombre}]
        assert comp.texto_derivado_motivos_comprobacion() == cat.nombre
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "motivo",
    [None, "", "PENDIENTE", "Motivo inventado CM1 xyz"],
)
def test_null_vacio_pendiente_y_desconocido_no_crean_vinculo(app_ctx, motivo) -> None:
    try:
        acta = _unique_acta()
        comp = Comprobacion(numero_acta=acta, anio=2026, mes=11, motivo=motivo)
        db.session.add(comp)
        db.session.flush()
        texto_antes = comp.motivo
        sync_unico_vinculo_desde_texto_historico(comp)
        db.session.flush()
        assert comp.motivo == texto_antes
        assert _ids_vinculos(comp) == []
        assert comp.texto_derivado_motivos_comprobacion() is None
        assert comp.motivos_comprobacion_as_dicts() == []
    finally:
        db.session.rollback()


def test_previas_pendiente_no_crea_vinculo_ni_altera_texto(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        acta = _unique_acta()
        resolver_previas(act, {"comprobacion_previa_num": acta})
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert comp is not None
        assert comp.motivo == "PENDIENTE"
        assert _ids_vinculos(comp) == []
    finally:
        db.session.rollback()


def test_no_permite_duplicar_mismo_motivo(app_ctx) -> None:
    try:
        cat = _catalogo_motivo()
        acta = _unique_acta()
        comp = Comprobacion(numero_acta=acta, anio=2026, mes=11, motivo=cat.nombre)
        db.session.add(comp)
        db.session.flush()
        set_motivos_catalogo(comp, [cat.nombre])
        db.session.flush()
        with pytest.raises(ValueError, match="no puede repetirse"):
            set_motivos_catalogo(comp, [cat.nombre, cat.nombre])
        with pytest.raises(IntegrityError):
            db.session.execute(
                comprobacion_motivo.insert().values(
                    comprobacion_id=int(comp.id),
                    catalog_motivo_comprobacion_id=int(cat.id),
                )
            )
            db.session.flush()
    finally:
        db.session.rollback()


def test_set_motivos_catalogo_admite_dos_distintos_ordenados(app_ctx) -> None:
    try:
        a, b = _dos_catalogo()
        acta = _unique_acta()
        comp = Comprobacion(numero_acta=acta, anio=2026, mes=11, motivo=a.nombre)
        db.session.add(comp)
        db.session.flush()
        set_motivos_catalogo(comp, [b.nombre, a.nombre])
        db.session.flush()
        esperados = sorted([a.nombre, b.nombre])
        assert [m.nombre for m in comp.motivos_comprobacion_ordenados()] == esperados
        assert (
            comp.texto_derivado_motivos_comprobacion()
            == SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(esperados)
        )
        assert comp.motivo == a.nombre
    finally:
        db.session.rollback()


def test_motivo_escalar_legado_sincroniza_unico_vinculo(app_ctx) -> None:
    try:
        a, b = _dos_catalogo()
        act = _mk_actuacion()
        acta = _unique_acta()
        attach_comprobacion(act, {"acta_num": acta, "motivo": a.nombre})
        db.session.flush()
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert comp is not None
        assert _ids_vinculos(comp) == [int(a.id)]

        attach_comprobacion(act, {"acta_num": acta, "motivo": b.nombre})
        db.session.flush()
        db.session.refresh(comp)
        assert comp.motivo == b.nombre
        assert _ids_vinculos(comp) == [int(b.id)]

        attach_comprobacion(act, {"acta_num": acta, "motivo": "Texto libre no catalogo CM1"})
        db.session.flush()
        db.session.refresh(comp)
        assert comp.motivo == "Texto libre no catalogo CM1"
        assert _ids_vinculos(comp) == []
    finally:
        db.session.rollback()


def test_endpoint_grid_conserva_payload_escalar(app_ctx) -> None:
    try:
        cat = _catalogo_motivo()
        act = _mk_actuacion()
        attach_comprobacion(act, {"acta_num": _unique_acta(), "motivo": cat.nombre})
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["comprobacion_motivo"] == cat.nombre
        assert "motivos_comprobacion" not in row
        dumped = act.comprobacion.to_dict()
        assert dumped["motivo"] == cat.nombre
        assert "motivos_comprobacion" not in dumped
    finally:
        db.session.rollback()
