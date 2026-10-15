"""Tests V1.1-MIG-ACTAS.1C — cadenas históricas por fases."""

from __future__ import annotations

import csv
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Tuple

import pytest

from app.database import db
from app.domains.migracion_historica.historico_cadenas_import_service import (
    ESTADO_VINCULO_CONFIABLE,
    ESTADO_VINCULO_REVISAR,
    FASE_1_RAIZ,
    FASE_2_REINSPECCION,
    FASE_3_OFICIO,
    MOTIVO_OFICIO_SIN_ORIGEN,
    MOTIVO_REINSPECCION_SIN_ORIGEN,
    clasificar_fase_importacion,
    enriquecer_planes_con_cadenas,
    importar_cadena_historica,
)
from app.domains.migracion_historica.historico_piloto_import_service import (
    DECISION_APPLICABLE,
    DECISION_REVISAR,
    PilotChainPlan,
    build_plan_from_sources,
    load_epicollect_by_uuid,
    run_pilot_import,
)
from app.domains.migracion_historica.epicollect_actas_inventario import (
    extract_row_snapshot,
    _header_indices,
)
from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (
    ESTADO_EVIDENCIA_FINALIZADA,
)
from app.models import Actuaciones, IniciadorRuta, Notificacion, RutaItem, RutaTrabajo
from app.utils.actas import acta_6

_MOTIVO_NOTIF = "Carnet de Sanidad"
_MOTIVO_COMP = "Falta de Higiene"
_RUBRO = "Comestibles"
_DNI = "20999888777"


def _hdr_extended() -> str:
    return (
        "ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N,3_Qu_inspectores_con,"
        "4_Domicilio,5_Pudo_realizar_la_i,6_Tipo_de_inspeccin,8_Numero_de_la_Notif,"
        "14_Nombre_de_Fantasa,15_Razn_Socialnombre,16_DNI_del_Contribuy,17_Rubro,"
        "80_Realizo_Acta_de_I,82_Numero_del_Acta_d,84_Realizo_Acta_de_N,86_Numero_del_Acta_d,"
        "87_Infracciones,91_Realizo_Acta_de_C,93_Numero_del_Acta_d,94_Infracciones,"
        "99_Realizo_Acta_de_C,101_Numero_de_Acta_d,103_Realizo_Acta_de_,105_Numero_de_Acta_d,"
        "107_Kilos_Decomisado,117_Numero_de_Expedi,118_Ao,119_Numero_de_Oficio"
    )


def _write_epi(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "epi.csv"
    body = "\n".join(rows)
    path.write_text(f"{_hdr_extended()}\n{body}\n", encoding="utf-8")
    return path


def _write_evidence(tmp_path: Path, pairs: list[tuple[str, str]]) -> Path:
    path = tmp_path / "ev.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["estado_coincidencia", "ec5_uuid", "legacy_ref_hash"],
        )
        w.writeheader()
        for ec5, leg in pairs:
            w.writerow(
                {
                    "estado_coincidencia": ESTADO_EVIDENCIA_FINALIZADA,
                    "ec5_uuid": ec5,
                    "legacy_ref_hash": leg,
                }
            )
    return path


def _plans_from_csv(app, epi: Path, ev: Path) -> list[PilotChainPlan]:
    from app.domains.migracion_historica.historico_piloto_import_service import load_evidence_finalizadas
    from app.models import Inspector, Motivo, Rubro, Turno
    from app.models.turno import TipoTurno

    _, ev_rows = load_evidence_finalizadas(ev)
    _, epi_by_uuid, raw_by_uuid = load_epicollect_by_uuid(epi)
    hdr_by_uuid = {}
    with epi.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        for row in reader:
            idx = hdr.index("ec5_uuid") if "ec5_uuid" in hdr else 0
            u = (row[idx] or "").strip()
            if u:
                hdr_by_uuid[u] = hdr
    with app.app_context():
        turno = Turno.query.first()
        if not turno:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()
        for m in (_MOTIVO_NOTIF, _MOTIVO_COMP):
            if not Motivo.query.filter_by(nombre=m).first():
                db.session.add(Motivo(nombre=m))
        if not Rubro.query.filter_by(nombre=_RUBRO).first():
            db.session.add(Rubro(nombre=_RUBRO))
        if not Inspector.query.filter_by(nombre="Inspector A").first():
            legajo = f"C{uuid.uuid4().hex[:4].upper()}"
            db.session.add(Inspector(nombre="Inspector A", legajo=legajo, turno_id=turno.id))
        db.session.commit()
        plans = build_plan_from_sources(
            ev_rows, epi_by_uuid, raw_by_uuid, hdr_by_uuid, date(2026, 10, 1)
        )
        enriquecer_planes_con_cadenas(plans, list(epi_by_uuid.values()))
    return plans


@pytest.fixture
def pilot_io_dirs(tmp_path: Path) -> Tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    return repo, out


def test_fase_1_raiz_con_notificacion(app, tmp_path: Path) -> None:
    u = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-03-01,10,Inspector A,Mitre 50,SI,Inspeccion,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,100001,SI,100002,{_MOTIVO_NOTIF},"
            "NO,,NO,,NO,,,,,"
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "h1")])
    plans = _plans_from_csv(app, epi, ev)
    assert plans[0].fase_importacion == FASE_1_RAIZ
    assert plans[0].decision == DECISION_APPLICABLE
    assert plans[0].estado_vinculo == ESTADO_VINCULO_CONFIABLE


def test_fase_1_comprobacion_y_clausura(app, tmp_path: Path) -> None:
    u = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-03-02,11,Inspector A,Mitre 51,SI,Inspeccion,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,100011,NO,,,SI,100012,{_MOTIVO_COMP},"
            f"SI,100013,NO,,NO,,,,,"
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "h2")])
    plans = _plans_from_csv(app, epi, ev)
    assert plans[0].fase_importacion == FASE_1_RAIZ
    assert plans[0].comprobacion
    assert plans[0].clausura


def test_fase_1_notificacion_y_comprobacion_sin_reinspeccion(app, tmp_path: Path) -> None:
    u = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-03-03,12,Inspector A,Mitre 52,SI,Inspeccion,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,100021,SI,100022,{_MOTIVO_NOTIF},"
            f"SI,100023,{_MOTIVO_COMP},NO,,NO,,,,"
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "h3")])
    plans = _plans_from_csv(app, epi, ev)
    assert plans[0].tipo_cadena == "inspeccion_notificacion_comprobacion"
    assert plans[0].fase_importacion == FASE_1_RAIZ


def test_reinspeccion_con_padre_valido(app, tmp_path: Path) -> None:
    root = str(uuid.uuid4())
    child = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{root},2024-01-10,20,Inspector A,Mitre 60,SI,Inspeccion,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,200001,SI,200002,{_MOTIVO_NOTIF},"
            "NO,,NO,,NO,,,,,",
            f"{child},2024-02-10,21,Inspector A,Mitre 60,SI,Reinspeccion por notificacion,200002,"
            f"Local SA,,{_DNI},{_RUBRO},SI,200101,NO,,NO,,"
            "NO,,NO,,NO,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(root, "r"), (child, "c")])
    plans = _plans_from_csv(app, epi, ev)
    child_plan = next(p for p in plans if p.ec5_uuid == child)
    assert child_plan.fase_importacion == FASE_2_REINSPECCION
    assert child_plan.estado_vinculo == ESTADO_VINCULO_CONFIABLE
    assert child_plan.parent_source_uuid == root


def test_reinspeccion_sin_padre_revisar(app, tmp_path: Path) -> None:
    child = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{child},2024-02-10,21,Inspector A,Mitre 60,SI,Reinspeccion por notificacion,999999,"
            f"Local SA,,{_DNI},{_RUBRO},SI,200101,NO,,NO,,"
            "NO,,NO,,NO,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(child, "c")])
    plans = _plans_from_csv(app, epi, ev)
    assert plans[0].decision == DECISION_REVISAR
    assert MOTIVO_REINSPECCION_SIN_ORIGEN in plans[0].motivo_revision


def test_reinspeccion_fecha_invalida_revisar(app, tmp_path: Path) -> None:
    root = str(uuid.uuid4())
    child = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{root},2024-03-10,20,Inspector A,Mitre 60,SI,Inspeccion,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,300001,SI,300002,{_MOTIVO_NOTIF},"
            "NO,,NO,,NO,,,,,",
            f"{child},2024-01-10,21,Inspector A,Mitre 60,SI,Reinspeccion por notificacion,300002,"
            f"Local SA,,{_DNI},{_RUBRO},SI,300101,NO,,NO,,"
            "NO,,NO,,NO,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(root, "r"), (child, "c")])
    plans = _plans_from_csv(app, epi, ev)
    child_plan = next(p for p in plans if p.ec5_uuid == child)
    assert child_plan.decision == DECISION_REVISAR


def test_oficio_sin_comprobacion_revisar(app, tmp_path: Path) -> None:
    u = str(uuid.uuid4())
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-04-01,30,Inspector A,Mitre 70,SI,Verificar e informar,,"
            f"Local SA,,{_DNI},{_RUBRO},SI,400001,NO,,NO,,"
            "NO,,NO,,NO,,100,2024,50",
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "o")])
    plans = _plans_from_csv(app, epi, ev)
    assert plans[0].fase_importacion == FASE_3_OFICIO
    assert plans[0].decision == DECISION_REVISAR
    assert MOTIVO_OFICIO_SIN_ORIGEN.split(":")[0] in plans[0].motivo_revision


def test_apply_fase_2_tras_raiz(
    app,
    tmp_path: Path,
    pilot_io_dirs: Tuple[Path, Path],
) -> None:
    from tests.test_importar_actas_historicas_piloto import _test_db_target

    from app.models import Inspector, Motivo, Rubro, Turno
    from app.models.turno import TipoTurno

    tag = uuid.uuid4().hex[:8]
    root = str(uuid.uuid4())
    child = str(uuid.uuid4())
    base = int(uuid.uuid4().hex[:6], 16) % 800000 + 100000
    acta_i = f"{base:06d}"
    acta_n = f"{base + 1:06d}"
    acta_r = f"{base + 2:06d}"
    odt_r = f"{base % 90000:05d}"
    odt_c = f"{(base + 1) % 90000:05d}"

    repo_root, output_dir = pilot_io_dirs
    epi = _write_epi(
        tmp_path,
        [
            f"{root},2024-01-15,{odt_r},Accardi Jose,Mitre 100,SI,Inspeccion,,"
            f"Pan SA,,20123456789,Comestibles,SI,{acta_i},SI,{acta_n},{_MOTIVO_NOTIF},"
            "NO,,NO,,NO,,,,,",
            f"{child},2024-02-15,{odt_c},Accardi Jose,Mitre 100,SI,Reinspeccion por notificacion,{acta_n},"
            f"Pan SA,,20123456789,Comestibles,SI,{acta_r},NO,,NO,,"
            "NO,,NO,,NO,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(root, "lr"), (child, "lc")])

    with app.app_context():
        turno = Turno.query.first()
        if not turno:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()
        if not Motivo.query.filter_by(nombre=_MOTIVO_NOTIF).first():
            db.session.add(Motivo(nombre=_MOTIVO_NOTIF))
        if not Rubro.query.filter_by(nombre="Comestibles").first():
            db.session.add(Rubro(nombre="Comestibles"))
        if not Inspector.query.filter_by(nombre="Accardi Jose").first():
            db.session.add(
                Inspector(
                    nombre="Accardi Jose",
                    legajo=f"A{uuid.uuid4().hex[:4].upper()}",
                    turno_id=turno.id,
                )
            )
        db.session.commit()

        rutas_antes = db.session.query(RutaTrabajo).count()
        items_antes = db.session.query(RutaItem).count()
        iniciadores_antes = db.session.query(IniciadorRuta).count()
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id=f"batch-cadena-{tag}",
            cutoff=date(2026, 10, 1),
            dry_run=False,
            apply=True,
            confirm_batch=f"batch-cadena-{tag}",
            target=_test_db_target(),
            repo_root=repo_root,
        )
        rein = Actuaciones.query.filter_by(ec5_uuid=child).one()
        assert rein.tipo == "REINSPECCION"
        assert rein.notificacion_id is not None
        noti = Notificacion.query.get(rein.notificacion_id)
        assert acta_6(noti.numero_acta) == acta_n
        assert db.session.query(RutaTrabajo).count() == rutas_antes
        assert db.session.query(RutaItem).count() == items_antes
        assert db.session.query(IniciadorRuta).count() == iniciadores_antes


def test_idempotencia_cadena(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    from tests.test_importar_actas_historicas_piloto import _test_db_target

    u = str(uuid.uuid4())
    tag = uuid.uuid4().hex[:6]
    base = int(uuid.uuid4().hex[:6], 16) % 800000 + 100000
    acta_i = f"{base:06d}"
    acta_n = f"{base + 1:06d}"
    acta_c = f"{base + 2:06d}"
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-05-10,{tag},Accardi Jose,Mitre 100,SI,Inicial,,"
            f"Pan SA,,20123456789,Comestibles,SI,{acta_i},SI,{acta_n},{_MOTIVO_NOTIF},"
            f"SI,{acta_c},Falta de Higiene,,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "x")])
    repo_root, output_dir = pilot_io_dirs
    kwargs = dict(
        output_dir=output_dir,
        epicollect_csv=epi,
        sandbox_evidence_csv=ev,
        batch_id=f"b-{tag}",
        cutoff=date(2026, 10, 1),
        dry_run=False,
        apply=True,
        confirm_batch=f"b-{tag}",
        target=_test_db_target(),
        repo_root=repo_root,
    )
    with app.app_context():
        from app.models import Inspector, Motivo, Rubro, Turno
        from app.models.turno import TipoTurno

        turno = Turno.query.first() or Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        for m in (_MOTIVO_NOTIF, _MOTIVO_COMP):
            if not Motivo.query.filter_by(nombre=m).first():
                db.session.add(Motivo(nombre=m))
        if not Rubro.query.filter_by(nombre="Comestibles").first():
            db.session.add(Rubro(nombre="Comestibles"))
        if not Inspector.query.filter_by(nombre="Accardi Jose").first():
            db.session.add(
                Inspector(
                    nombre="Accardi Jose",
                    legajo=f"Z{uuid.uuid4().hex[:4].upper()}",
                    turno_id=turno.id,
                )
            )
        db.session.commit()

        r1 = run_pilot_import(**kwargs)
        r2 = run_pilot_import(**kwargs)
        assert r1.resumen["insertadas"] == 1
        assert r2.resumen["omitidas_idempotencia"] == 1


def test_rollback_cadena_fallida(
    app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_importar_actas_historicas_piloto import _test_db_target

    u = str(uuid.uuid4())
    tag = uuid.uuid4().hex[:6]
    epi = _write_epi(
        tmp_path,
        [
            f"{u},2024-05-11,{tag},Accardi José,Mitre 100,SI,Inicial,,"
            f"Pan SA,,20123456789,Comestibles,SI,700001,SI,700002,{_MOTIVO_NOTIF},"
            "NO,,NO,,NO,,,,,",
        ],
    )
    ev = _write_evidence(tmp_path, [(u, "y")])
    repo_root, output_dir = pilot_io_dirs

    def _boom(plan):  # noqa: ANN001
        raise ValueError("fallo_simulado")

    monkeypatch.setattr(
        "app.domains.migracion_historica.historico_piloto_import_service.importar_cadena_historica",
        lambda plan: _boom(plan),
    )
    with app.app_context():
        from app.models import Inspector, Motivo, Rubro, Turno
        from app.models.turno import TipoTurno

        turno = Turno.query.first() or Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        if not Motivo.query.filter_by(nombre=_MOTIVO_NOTIF).first():
            db.session.add(Motivo(nombre=_MOTIVO_NOTIF))
        if not Rubro.query.filter_by(nombre="Comestibles").first():
            db.session.add(Rubro(nombre="Comestibles"))
        db.session.add(
            Inspector(
                nombre="Accardi Jose",
                legajo=f"Y{uuid.uuid4().hex[:4].upper()}",
                turno_id=turno.id,
            )
        )
        db.session.commit()
        before = Actuaciones.query.count()
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id=f"rb-{tag}",
            cutoff=date(2026, 10, 1),
            dry_run=False,
            apply=True,
            confirm_batch=f"rb-{tag}",
            target=_test_db_target(),
            repo_root=repo_root,
        )
        assert Actuaciones.query.count() == before
