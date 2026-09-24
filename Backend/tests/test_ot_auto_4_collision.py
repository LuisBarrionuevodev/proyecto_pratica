"""OT-AUTO.4 — colisión, preview compartido, concurrencia y rollback."""

from __future__ import annotations

import random
import threading
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    allocar_rango_orden_trabajo,
    patch_contador_admin,
    preview_secuencia_ot,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import OrdenTrabajo, RutaTrabajo
from app.utils.actas import format_ot_display
from tests.helpers.ot_auto_collision import (
    ensure_legacy_ot,
    expected_displays,
    fresh_collision_band,
    publish_n_items,
    read_counter,
    set_counter_force,
)
from tests.test_ot_auto_3_secuencia import (
    _borrador_con_n_iniciadores,
    _mk_iniciador,
    _mk_user,
)


def _assert_simple_contract(band: int, displays: list[str], next_v: int, count: int = 5) -> None:
    """Contrato isomorfo al ticket 4000/004003: un ocupado en +3."""
    exp_nums = [band, band + 1, band + 2, band + 4, band + 5]
    assert [int(d) for d in displays] == exp_nums
    assert next_v == band + 6
    assert len(displays) == count


def _assert_multiple_contract(band: int, displays: list[str], next_v: int) -> None:
    exp_nums = [band, band + 3, band + 5, band + 6, band + 7]
    assert [int(d) for d in displays] == exp_nums
    assert next_v == band + 8


def test_collision_simple(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2091)
    assert [int(x) for x in expected_displays(band, 5)] == [band + i for i in (0, 1, 2, 4, 5)]

    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 5)
    _assert_simple_contract(band, displays, next_v)


def test_collision_multiple(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    for off in (1, 2, 4):
        ensure_legacy_ot(format_ot_display(band + off), anio=2092)
    assert [int(x) for x in expected_displays(band, 5)] == [band + i for i in (0, 3, 5, 6, 7)]

    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 5)
    _assert_multiple_contract(band, displays, next_v)


def test_collision_first_occupied(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band), anio=2093)
    exp = expected_displays(band, 2)
    assert [int(x) for x in exp] == [band + 1, band + 2]

    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 2)
    assert [int(d) for d in displays] == [band + 1, band + 2]
    assert next_v == band + 3


def test_collision_soft_deleted(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2094, soft_deleted=True)
    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 5)
    assert format_ot_display(band + 3) not in displays
    _assert_simple_contract(band, displays, next_v)


def test_collision_cross_year(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2024)
    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 5, fecha_year=2026)
    assert format_ot_display(band + 3) not in displays
    _assert_simple_contract(band, displays, next_v)


def test_collision_auto_existente(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(
        format_ot_display(band + 3),
        anio=2095,
        numero_secuencia_global=band + 3,
    )
    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 5)
    _assert_simple_contract(band, displays, next_v)


def test_collision_contiguous_block(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    for off in range(5):
        ensure_legacy_ot(format_ot_display(band + off), anio=2096)
    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 2)
    assert [int(d) for d in displays] == [band + 5, band + 6]
    assert next_v == band + 7


def test_preview_collision_no_writes(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2097)
    before = read_counter()
    ot_before = OrdenTrabajo.query.count()

    p = preview_secuencia_ot(count=5)
    assert p.first_display == format_ot_display(band)
    assert p.last_display == format_ot_display(band + 5)
    assert p.skipped_count == 1
    assert [int(x) for x in p.displays] == [band + i for i in (0, 1, 2, 4, 5)]

    assert read_counter() == before
    assert OrdenTrabajo.query.count() == ot_before


def test_preview_vs_publish_race(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2098)
    p = preview_secuencia_ot(count=5)
    race_target = p.displays[3]
    ensure_legacy_ot(race_target, anio=2098)
    exp_after_race = expected_displays(band, 5)

    u = _mk_user()
    displays, _ = publish_n_items(u.id, 5)
    assert race_target not in displays
    assert displays == exp_after_race
    assert len(set(displays)) == 5


def test_rollback_with_skips(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 3), anio=2099)
    u = _mk_user()
    inis = [_mk_iniciador(u.id) for _ in range(5)]
    ruta, _ = _borrador_con_n_iniciadores(u.id, inis)

    def _alloc_then_fail(**kwargs):
        allocar_rango_orden_trabajo(**kwargs)
        raise RuntimeError("simulated failure after alloc")

    with patch(
        "app.domains.rutas_trabajo.services.ruta_publicar_service.allocar_rango_orden_trabajo",
        side_effect=_alloc_then_fail,
    ):
        with pytest.raises(RuntimeError, match="simulated"):
            publicar_ruta_trabajo(ruta_id=ruta.id)

    db.session.expire_all()
    assert read_counter() == band
    ruta_db = RutaTrabajo.query.get(ruta.id)
    assert ruta_db is not None
    assert ruta_db.estado_ruta == "BORRADOR"


def test_concurrent_publish_with_legacy_skips(app_ctx) -> None:
    band = fresh_collision_band()
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band + 1), anio=2100)
    u = _mk_user()
    rutas: list[RutaTrabajo] = []
    for i in range(2):
        ini = _mk_iniciador(u.id)
        ruta, _ = _borrador_con_n_iniciadores(
            u.id, [ini], fecha=date(2026, 7, 1) + timedelta(days=i)
        )
        rutas.append(ruta)

    results: list[list[str]] = []
    errors: list[Exception] = []

    def _pub(ruta_id: int) -> None:
        from app import create_app

        app = create_app({"TESTING": True})
        with app.app_context():
            try:
                _, _, meta = publicar_ruta_trabajo(ruta_id=ruta_id)
                results.append([a["numero_acta"] for a in meta["ordenes_asignadas"]])
            except Exception as exc:
                errors.append(exc)

    t1 = threading.Thread(target=_pub, args=(rutas[0].id,))
    t2 = threading.Thread(target=_pub, args=(rutas[1].id,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors
    all_nums = results[0] + results[1]
    assert len(all_nums) == 2
    assert len(set(all_nums)) == 2
    assert format_ot_display(band + 1) not in all_nums
    db.session.remove()
    assert read_counter() == band + 3


def test_patch_counter_to_occupied_normalizes(app_ctx) -> None:
    admin = _mk_user(role="admin")
    from tests.helpers.ot_auto_collision import fresh_collision_band, set_counter_force

    base = fresh_collision_band(width=1200)
    set_counter_force(base)
    ensure_legacy_ot(format_ot_display(base + 1000), anio=2101)
    ensure_legacy_ot(format_ot_display(base + 1001), anio=2101)

    requested = base + 1000
    old, effective, display, req = patch_contador_admin(
        new_value=requested,
        reason="QA salto a ocupado",
        actor_user_id=admin.id,
    )
    db.session.commit()
    assert old == base
    assert req == requested
    assert effective == base + 1002
    assert display == format_ot_display(base + 1002)
