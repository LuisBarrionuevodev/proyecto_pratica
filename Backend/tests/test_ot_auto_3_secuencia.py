"""OT-AUTO.3 — secuencia global, publicación automática y contador admin."""

from __future__ import annotations

import random
import threading
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
    allocar_rango_orden_trabajo,
    leer_contador_readonly,
    next_available_candidates,
    patch_contador_admin,
    preview_secuencia_ot,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import set_orden_trabajo_on_item
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Domicilio,
    IniciadorRuta,
    OrdenTrabajo,
    OrdenTrabajoContador,
    RutaItem,
    RutaTrabajo,
    User,
)
from app.utils.actas import format_ot_display
from tests.helpers.ruta_ot_test import asignar_ot_legacy_en_item


def _unique_num() -> str:
    return f"{random.randint(900000, 999998):06d}"


def _mk_user(role: str = "usuario") -> User:
    u = User(
        username=f"u_otauto_{_unique_num()}",
        email=f"otauto_{_unique_num()}@t.local",
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _dos_inspectores():
    from app.models import Inspector

    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores")
    return rows[0], rows[1]


def _set_counter(value: int) -> int:
    """Fija contador al primer entero libre >= value (evita colisiones en test DB)."""
    from app.domains.orden_trabajo.services.orden_trabajo_secuencia_service import (
        _primer_asignable_desde,
    )

    effective = _primer_asignable_desde(int(value))
    row = OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc()).first()
    assert row is not None
    row.next_value = effective
    db.session.add(row)
    db.session.commit()
    return effective


def _mk_iniciador(uid: int) -> IniciadorRuta:
    dom = Domicilio(calle=f"OtAuto_{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="PENDIENTE",
        fecha_origen=date.today(),
        anio=date.today().year,
        mes=date.today().month,
        domicilio_id=dom.id,
        created_by_user_id=uid,
    )
    db.session.add(ini)
    db.session.flush()
    db.session.commit()
    return ini


def _borrador_con_n_iniciadores(
    uid: int,
    iniciadores: list[IniciadorRuta],
    *,
    fecha: date | None = None,
) -> tuple[RutaTrabajo, list[RutaItem]]:
    ins1, ins2 = _dos_inspectores()
    f = fecha or (date(2026, 3, 15) + timedelta(days=random.randint(0, 30)))
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=uid,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="G OT-AUTO", estado="ACTIVO", actor_user_id=uid)
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
        actor_user_id=uid,
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[i.id for i in iniciadores],
        actor_user_id=uid,
    )
    db.session.commit()
    return ruta, items


def test_migration_counter_exists(app_ctx) -> None:
    row = OrdenTrabajoContador.query.first()
    assert row is not None
    assert int(row.next_value) >= 89862


def test_format_ot_display_million() -> None:
    assert format_ot_display(89862) == "089862"
    assert format_ot_display(999999) == "999999"
    assert format_ot_display(1000000) == "1000000"


def test_publicar_1_item_asigna_ot(app_ctx) -> None:
    base = _set_counter(970000 + random.randint(0, 500))
    u = _mk_user()
    ini = _mk_iniciador(u.id)
    ruta, items = _borrador_con_n_iniciadores(u.id, [ini])
    _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item = RutaItem.query.get(items[0].id)
    assert item is not None and item.orden_trabajo_id is not None
    ot = OrdenTrabajo.query.get(item.orden_trabajo_id)
    assert ot is not None
    assert ot.numero_secuencia_global == base
    assert ot.numero_acta == format_ot_display(base)
    assert meta["next_value"] == base + 1


def test_publicar_n_items_secuencial(app_ctx) -> None:
    _set_counter(971000 + random.randint(0, 200))
    preview = preview_secuencia_ot(count=3)
    expected = list(preview.displays)
    _, _, next_after = next_available_candidates(preview.next_value, 3)
    u = _mk_user()
    inis = [_mk_iniciador(u.id) for _ in range(3)]
    ruta, items = _borrador_con_n_iniciadores(u.id, inis)
    _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    displays = sorted(a["numero_acta"] for a in meta["ordenes_asignadas"])
    assert displays == sorted(expected)
    assert meta["next_value"] == next_after


def test_skip_legacy_numero_ocupado(app_ctx) -> None:
    base = _set_counter(972100 + random.randint(0, 50))
    legacy_display = format_ot_display(base + 1)
    if not OrdenTrabajo.query.filter_by(numero_acta=legacy_display).first():
        db.session.add(
            OrdenTrabajo(
                numero_acta=legacy_display,
                numero_secuencia_global=None,
                anio=2020,
                mes=1,
            )
        )
        db.session.commit()

    expected = preview_secuencia_ot(count=3).displays

    u = _mk_user()
    inis = [_mk_iniciador(u.id) for _ in range(3)]
    ruta, _items = _borrador_con_n_iniciadores(u.id, inis)
    _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    displays = [a["numero_acta"] for a in meta["ordenes_asignadas"]]
    assert displays == list(expected)
    assert legacy_display not in displays


def test_legacy_preasignada_preservada(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u.id)
    ruta, items = _borrador_con_n_iniciadores(u.id, [ini])
    legacy_num = _unique_num()
    asignar_ot_legacy_en_item(ruta_id=ruta.id, item_id=items[0].id, numero_orden_trabajo=legacy_num)
    _, _, meta = publicar_ruta_trabajo(ruta_id=ruta.id)
    assert meta["ordenes_asignadas"][0]["modo"] == "legacy_preasignada"
    assert meta["ordenes_asignadas"][0]["numero_acta"] == legacy_num.zfill(6)


def test_manual_patch_endpoint_disabled(app_ctx) -> None:
    u = _mk_user()
    ini = _mk_iniciador(u.id)
    ruta, items = _borrador_con_n_iniciadores(u.id, [ini])
    with pytest.raises(RuntimeError, match="OT-AUTO"):
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=items[0].id,
            numero_orden_trabajo="123456",
        )


def test_patch_contador_admin_forward(app_ctx) -> None:
    admin = _mk_user(role="admin")
    base = _set_counter(973000 + random.randint(0, 99))
    old, effective, display, requested = patch_contador_admin(
        new_value=base + 5,
        reason="QA adelanto contador",
        actor_user_id=admin.id,
    )
    db.session.commit()
    assert old == base
    assert effective == base + 5
    assert display == format_ot_display(base + 5)
    assert requested == base + 5


def test_patch_contador_reject_below_minimum(app_ctx) -> None:
    admin = _mk_user(role="admin")
    _set_counter(974000)
    with pytest.raises(ValueError, match=">= 1"):
        patch_contador_admin(
            new_value=0,
            reason="intento valor inválido",
            actor_user_id=admin.id,
        )


def test_preview_skip_count(app_ctx) -> None:
    base = _set_counter(975000)
    legacy_display = format_ot_display(base + 1)
    if not OrdenTrabajo.query.filter_by(numero_acta=legacy_display).first():
        db.session.add(OrdenTrabajo(numero_acta=legacy_display, anio=2099, mes=6))
        db.session.commit()
    p = preview_secuencia_ot(count=3)
    assert p.skipped_count == 1
    assert list(p.displays) == [
        format_ot_display(base),
        format_ot_display(base + 2),
        format_ot_display(base + 3),
    ]


def test_concurrent_publish_disjoint_ranges(app_ctx) -> None:
    """Dos publicaciones concurrentes: rangos disjuntos (lock real, sin mock)."""
    base = _set_counter(976000)
    u = _mk_user()
    rutas: list[RutaTrabajo] = []
    for _ in range(2):
        ini = _mk_iniciador(u.id)
        ruta, _ = _borrador_con_n_iniciadores(u.id, [ini], fecha=date(2026, 4, 1) + timedelta(days=len(rutas)))
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
            except Exception as e:
                errors.append(e)

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
    db.session.remove()
    row = OrdenTrabajoContador.query.order_by(OrdenTrabajoContador.id.asc()).first()
    assert row is not None
    assert int(row.next_value) == base + 2
    assigned_nums = sorted(int(n.lstrip("0") or "0") for n in all_nums)
    assert assigned_nums == [base, base + 1]
