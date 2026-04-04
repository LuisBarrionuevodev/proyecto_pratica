"""
Congela la Fase A: actuación base (max id) y estados bloqueantes para REINSPECCION_NOTIFICACION.
Fase B: idempotencia ante IntegrityError (único en BD) y mocks de sesión para sync sin app context.
"""

from __future__ import annotations

import contextlib
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

import app.domains.actuaciones.services.notificacion_iniciador_service as notificacion_iniciador_service
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    _agrupar_eligible_por_notificacion_id,
    elegir_actuacion_base_inspeccion_para_notificacion,
    estado_bloquea_nueva_materializacion_reinspeccion_notificacion,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados


def test_elegir_actuacion_base_toma_mayor_id():
    a = SimpleNamespace(id=1, notificacion_id=10)
    b = SimpleNamespace(id=3, notificacion_id=10)
    c = SimpleNamespace(id=2, notificacion_id=10)
    elegido = elegir_actuacion_base_inspeccion_para_notificacion([a, b, c])
    assert elegido.id == 3


def test_elegir_actuacion_base_vacio():
    assert elegir_actuacion_base_inspeccion_para_notificacion([]) is None


def test_agrupar_por_notificacion_elige_max_id_por_grupo():
    acts = [
        SimpleNamespace(id=10, notificacion_id=5),
        SimpleNamespace(id=20, notificacion_id=5),
        SimpleNamespace(id=15, notificacion_id=7),
    ]
    m = _agrupar_eligible_por_notificacion_id(acts)
    assert m[5].id == 20
    assert m[7].id == 15
    assert len(m) == 2


@pytest.mark.parametrize(
    "estado,espera_bloquea",
    [
        ("PENDIENTE", True),
        ("PLANIFICADO", True),
        ("EN_EJECUCION", True),
        ("CUMPLIDO", True),
        ("NO_REALIZADO_REPROGRAMAR", True),
        ("ANULADO", False),
        ("CERRADO", False),
        ("CERRADO_NO_EXISTE_LOCAL", False),
        (None, False),
    ],
)
def test_matriz_estado_bloquea_nueva_materializacion(estado, espera_bloquea):
    assert (
        estado_bloquea_nueva_materializacion_reinspeccion_notificacion(estado) == espera_bloquea
    )


def test_estados_no_bloqueantes_coinciden_con_inactive_estados():
    for s in inactive_estados():
        assert estado_bloquea_nueva_materializacion_reinspeccion_notificacion(s) is False


def _patch_session_sync_unit(monkeypatch):
    """Sync sin contexto Flask ni DB: savepoint simulado + flush no-op."""
    monkeypatch.setattr(
        notificacion_iniciador_service.db.session,
        "begin_nested",
        lambda: contextlib.nullcontext(),
    )
    monkeypatch.setattr(notificacion_iniciador_service.db.session, "flush", lambda: None)


def test_sync_segunda_corrida_no_agrega_cuando_existe_bloqueo(monkeypatch):
    """
    Primera corrida: sin bloqueo → 1 alta. Segunda: existe bloqueo → 0 altas (idempotencia lógica).
    """
    today = date.today()
    noti = SimpleNamespace(
        id=99,
        fecha_vencimiento=today,
        deleted_at=None,
        numero_acta="000001",
        anio=2026,
    )
    act = SimpleNamespace(id=42, notificacion_id=99, domicilio_id=1, notificacion=noti)

    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_eligible_inspecciones_vencidas",
        lambda: [act],
    )
    monkeypatch.setattr(notificacion_iniciador_service, "_get_current_user_id", lambda: 1)

    calls = {"n": 0}

    def exists_side_effect(nid: int) -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion",
        exists_side_effect,
    )

    _patch_session_sync_unit(monkeypatch)

    adds: list = []

    def capture_add(obj):
        adds.append(obj)

    monkeypatch.setattr(notificacion_iniciador_service.db.session, "add", capture_add)
    monkeypatch.setattr(notificacion_iniciador_service.db.session, "commit", lambda: None)

    o1 = sync_iniciadores_reinspeccion_notificacion()
    assert o1.created == 1
    assert len(adds) == 1

    o2 = sync_iniciadores_reinspeccion_notificacion()
    assert o2.created == 0
    assert o2.skipped_already_blocking >= 1
    assert len(adds) == 1


def test_sync_cero_altas_si_bloqueo_desde_el_inicio(monkeypatch):
    today = date.today()
    noti = SimpleNamespace(
        id=88,
        fecha_vencimiento=today,
        deleted_at=None,
        numero_acta="000002",
        anio=2026,
    )
    act = SimpleNamespace(id=50, notificacion_id=88, domicilio_id=1, notificacion=noti)

    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_eligible_inspecciones_vencidas",
        lambda: [act],
    )
    monkeypatch.setattr(notificacion_iniciador_service, "_get_current_user_id", lambda: 1)
    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion",
        lambda nid: True,
    )

    _patch_session_sync_unit(monkeypatch)

    adds: list = []

    def capture_add(obj):
        adds.append(obj)

    monkeypatch.setattr(notificacion_iniciador_service.db.session, "add", capture_add)
    monkeypatch.setattr(notificacion_iniciador_service.db.session, "commit", lambda: None)

    z1 = sync_iniciadores_reinspeccion_notificacion()
    z2 = sync_iniciadores_reinspeccion_notificacion()
    assert z1.created == 0 and z2.created == 0
    assert z1.skipped_already_blocking == 1
    assert adds == []


def test_sync_integrity_error_es_idempotente_sin_commit(monkeypatch):
    """
    Fase B: colisión única en flush (carrera / doble sync) → 0 creados, sin propagar error.
    """
    today = date.today()
    noti = SimpleNamespace(
        id=77,
        fecha_vencimiento=today,
        deleted_at=None,
        numero_acta="000003",
        anio=2026,
    )
    act = SimpleNamespace(id=60, notificacion_id=77, domicilio_id=1, notificacion=noti)

    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_eligible_inspecciones_vencidas",
        lambda: [act],
    )
    monkeypatch.setattr(notificacion_iniciador_service, "_get_current_user_id", lambda: 1)
    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion",
        lambda nid: False,
    )

    _patch_session_sync_unit(monkeypatch)

    commits: list = []

    def flush_raises():
        raise IntegrityError("mock", {}, None)

    monkeypatch.setattr(notificacion_iniciador_service.db.session, "flush", flush_raises)
    monkeypatch.setattr(notificacion_iniciador_service.db.session, "add", lambda o: None)
    monkeypatch.setattr(
        notificacion_iniciador_service.db.session,
        "commit",
        lambda: commits.append(1),
    )

    o = sync_iniciadores_reinspeccion_notificacion()
    assert o.created == 0
    assert o.collisions_idempotent == 1
    assert commits == []


def test_sync_doble_corrida_integrity_luego_exito(monkeypatch):
    """
    Primera corrida: IntegrityError (otro proceso insertó). Segunda: sin colisión → 1 alta.
    """
    today = date.today()
    noti = SimpleNamespace(
        id=66,
        fecha_vencimiento=today,
        deleted_at=None,
        numero_acta="000004",
        anio=2026,
    )
    act = SimpleNamespace(id=61, notificacion_id=66, domicilio_id=1, notificacion=noti)

    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_eligible_inspecciones_vencidas",
        lambda: [act],
    )
    monkeypatch.setattr(notificacion_iniciador_service, "_get_current_user_id", lambda: 1)
    monkeypatch.setattr(
        notificacion_iniciador_service,
        "_exists_iniciador_reinspeccion_notificacion_que_bloquea_nueva_materializacion",
        lambda nid: False,
    )

    _patch_session_sync_unit(monkeypatch)

    flush_n = {"n": 0}

    def flush_maybe_raise():
        flush_n["n"] += 1
        if flush_n["n"] == 1:
            raise IntegrityError("mock", {}, None)

    monkeypatch.setattr(
        notificacion_iniciador_service.db.session,
        "flush",
        flush_maybe_raise,
    )

    adds: list = []

    def capture_add(obj):
        adds.append(obj)

    monkeypatch.setattr(notificacion_iniciador_service.db.session, "add", capture_add)
    monkeypatch.setattr(notificacion_iniciador_service.db.session, "commit", lambda: None)

    a = sync_iniciadores_reinspeccion_notificacion()
    b = sync_iniciadores_reinspeccion_notificacion()
    assert a.created == 0 and a.collisions_idempotent == 1
    assert b.created == 1 and b.collisions_idempotent == 0
    assert len(adds) == 2
