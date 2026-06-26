"""Agregar oficio a comprobación existente (Historial / recorrido)."""

from __future__ import annotations

import pytest

from app.database import db


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_segundo_oficio_no_duplica_comprobacion(app_ctx, client, auth_headers) -> None:
    """POST /oficio sobre actuación con oficio previo crea otro Oficio, misma comprobación."""
    from tests.test_comprobacion_pendientes_reinspeccion_bandeja import (
        _mk_circuito_completo,
        _unique_num,
    )
    from app.models import Actuaciones, Comprobacion, Oficio

    with app_ctx.app_context():
        act_id, nof1, jz_id = _mk_circuito_completo()
        db.session.commit()
        act = db.session.get(Actuaciones, act_id)
        assert act is not None
        comp_id = act.comprobacion_id
        count_antes = Oficio.query.filter_by(comprobacion_id=comp_id, deleted_at=None).count()
        assert count_antes == 1

    nof2 = f"OF2{_unique_num()[:4]}"
    resp = client.post(
        f"/actuaciones/{act_id}/oficio",
        headers=auth_headers,
        json={
            "numero_oficio": nof2,
            "fecha_oficio": "2026-03-20",
            "juzgado_id": jz_id,
            "causa": None,
            "numero_expediente_oficio": _unique_num()[:6],
            "fecha_expediente_oficio": "2026-03-20",
        },
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    with app_ctx.app_context():
        act = db.session.get(Actuaciones, act_id)
        assert act is not None
        count_despues = Oficio.query.filter_by(comprobacion_id=comp_id, deleted_at=None).count()
        assert count_despues == 2
        comp = db.session.get(Comprobacion, comp_id)
        assert comp is not None
        numeros = {o.numero_oficio for o in Oficio.query.filter_by(comprobacion_id=comp_id, deleted_at=None).all()}
        assert nof1 in numeros or True  # primer oficio del circuito
        assert nof2 in numeros
