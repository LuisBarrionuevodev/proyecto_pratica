"""OT-AUTO.6 — reposición segura del cursor OT (backward + forward)."""

from __future__ import annotations

import threading

import pytest

from app.database import db
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    patch_contador_admin,
    preview_secuencia_ot,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import OrdenTrabajo, OrdenTrabajoContadorAudit
from app.utils.actas import format_ot_display
from tests.helpers.ot_auto_collision import (
    ensure_legacy_ot,
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


def _cursor_high(band: int) -> int:
    """Simula cursor en 8003 con banda base en 4000."""
    return band + 43


def test_backward_free(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=50)
    high = _cursor_high(band)
    set_counter_force(high)

    old, effective, display, requested = patch_contador_admin(
        new_value=band,
        reason="QA backward libre",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == high
    assert requested == band
    assert effective == band
    assert display == format_ot_display(band)
    assert read_counter() == band


def test_backward_occupied(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=50)
    high = _cursor_high(band)
    set_counter_force(high)
    ensure_legacy_ot(format_ot_display(band), anio=2110)
    ensure_legacy_ot(format_ot_display(band + 1), anio=2110)

    old, effective, display, requested = patch_contador_admin(
        new_value=band,
        reason="QA backward ocupado",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == high
    assert requested == band
    assert effective == band + 2
    assert display == format_ot_display(band + 2)


def test_forward_still_works(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=50)
    set_counter_force(band)
    target = band + 50

    old, effective, display, requested = patch_contador_admin(
        new_value=target,
        reason="QA forward",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == band
    assert requested == target
    assert effective == target
    assert display == format_ot_display(target)


def test_same_value_free_no_op(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=10)
    set_counter_force(band)

    old, effective, display, requested = patch_contador_admin(
        new_value=band,
        reason="QA mismo valor libre",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == band
    assert effective == band
    assert display == format_ot_display(band)
    assert requested == band
    audits = OrdenTrabajoContadorAudit.query.filter_by(user_id=admin.id).count()
    assert audits == 0


def test_same_value_occupied_normalizes(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=10)
    set_counter_force(band)
    ensure_legacy_ot(format_ot_display(band), anio=2111)

    old, effective, display, requested = patch_contador_admin(
        new_value=band,
        reason="QA mismo valor ocupado",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == band
    assert requested == band
    assert effective == band + 1
    assert display == format_ot_display(band + 1)


def test_publish_after_backward(app_ctx) -> None:
    admin = _mk_user(role="admin")
    u = _mk_user()
    band = fresh_collision_band(width=20)
    set_counter_force(_cursor_high(band))

    patch_contador_admin(
        new_value=band,
        reason="QA publicar tras backward",
        actor_user_id=admin.id,
    )
    db.session.commit()

    displays, next_v = publish_n_items(u.id, 3)
    assert displays == [
        format_ot_display(band),
        format_ot_display(band + 1),
        format_ot_display(band + 2),
    ]
    assert next_v == band + 3


def test_skip_old_qa_range(app_ctx) -> None:
    band = fresh_collision_band(width=40)
    qa_start = band + 30
    for off in range(3):
        ensure_legacy_ot(format_ot_display(qa_start + off), anio=2112)
    set_counter_force(qa_start)

    u = _mk_user()
    displays, next_v = publish_n_items(u.id, 2)
    assert displays == [
        format_ot_display(qa_start + 3),
        format_ot_display(qa_start + 4),
    ]
    assert next_v == qa_start + 5


def test_backward_skip_soft_deleted(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=20)
    ensure_legacy_ot(format_ot_display(band), anio=2113, soft_deleted=True)
    set_counter_force(band + 10)

    old, effective, _, _ = patch_contador_admin(
        new_value=band,
        reason="QA skip soft-deleted",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == band + 10
    assert effective == band + 1


def test_backward_skip_cross_year(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=20)
    ensure_legacy_ot(format_ot_display(band), anio=2019)
    set_counter_force(band + 10)

    old, effective, _, _ = patch_contador_admin(
        new_value=band,
        reason="QA skip cross-year",
        actor_user_id=admin.id,
    )
    db.session.commit()

    assert old == band + 10
    assert effective == band + 1


def test_backward_preview_after_patch(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=20)
    set_counter_force(_cursor_high(band))

    patch_contador_admin(
        new_value=band,
        reason="QA preview",
        actor_user_id=admin.id,
    )
    db.session.commit()

    p = preview_secuencia_ot(count=1)
    assert p.next_value == band
    assert p.next_display == format_ot_display(band)
    assert p.first_display == format_ot_display(band)


def test_backward_preview_with_occupied_normalization(app_ctx) -> None:
    admin = _mk_user(role="admin")
    band = fresh_collision_band(width=20)
    ensure_legacy_ot(format_ot_display(band), anio=2114)
    ensure_legacy_ot(format_ot_display(band + 1), anio=2114)
    set_counter_force(_cursor_high(band))

    patch_contador_admin(
        new_value=band,
        reason="QA preview ocupado",
        actor_user_id=admin.id,
    )
    db.session.commit()

    p = preview_secuencia_ot(count=1)
    assert p.next_value == band + 2
    assert p.next_display == format_ot_display(band + 2)
    assert p.first_display == format_ot_display(band + 2)


def test_concurrent_patch_backward_and_publish(app_ctx) -> None:
    band = fresh_collision_band(width=30)
    set_counter_force(_cursor_high(band))
    u = _mk_user(role="admin")
    actor = _mk_user()
    ini = _mk_iniciador(actor.id)
    ruta, _ = _borrador_con_n_iniciadores(actor.id, [ini])

    patch_out: list[tuple[int, int]] = []
    pub_out: list[list[str]] = []
    errors: list[Exception] = []

    def _patch() -> None:
        from app import create_app

        app = create_app({"TESTING": True})
        with app.app_context():
            try:
                old_v, eff_v, _, _ = patch_contador_admin(
                    new_value=band,
                    reason="QA concurrent patch",
                    actor_user_id=u.id,
                )
                db.session.commit()
                patch_out.append((old_v, eff_v))
            except Exception as exc:
                errors.append(exc)

    def _publish() -> None:
        from app import create_app

        app = create_app({"TESTING": True})
        with app.app_context():
            try:
                _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
                pub_out.append([a["numero_acta"] for a in meta["ordenes_asignadas"]])
            except Exception as exc:
                errors.append(exc)

    t1 = threading.Thread(target=_patch)
    t2 = threading.Thread(target=_publish)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors
    all_displays = pub_out[0] if pub_out else []
    if patch_out:
        _, effective = patch_out[0]
        assert read_counter() >= effective
    if all_displays:
        assert len(all_displays) == len(set(all_displays))
        for disp in all_displays:
            assert OrdenTrabajo.query.filter_by(numero_acta=disp).count() == 1
