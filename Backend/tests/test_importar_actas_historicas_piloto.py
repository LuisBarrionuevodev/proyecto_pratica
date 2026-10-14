"""Tests piloto importación histórica V1.1-MIG-ACTAS.1A."""

from __future__ import annotations

import csv
import json
import os
import runpy
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Tuple

import pytest

from app.database import db
from app.domains.migracion_historica.historico_migracion_import_security import (
    HistoricoMigracionImportSecurityError,
    MigracionImportTarget,
    validate_migracion_import_database_uri,
)
from app.domains.migracion_historica.migracion_target_connection import (
    MigracionTargetConnectionError,
    pin_explicit_database_uri,
)
from app.domains.migracion_historica.historico_piloto_import_service import (
    DECISION_INSERTED,
    DECISION_REVISAR,
    SOURCE_NAME,
    build_plan_from_sources,
    count_operational_tables,
    load_evidence_finalizadas,
    run_pilot_import,
)
from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (
    ESTADO_EVIDENCIA_FINALIZADA as EVID_FINAL,
)
from app.models import (
    Actuaciones,
    IniciadorRuta,
    Inspector,
    MigracionHistoricaRegistro,
    Motivo,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    Turno,
)
from app.models.turno import TipoTurno

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND_ROOT / "scripts" / "importar_actas_historicas_piloto.py"
MIGRACION_URI = "mysql+pymysql://root:secret@127.0.0.1:3306/digitaliza_migracion"
SANDBOX_URI = "mysql+pymysql://root:secret@127.0.0.1:3306/digitaliza_sandbox"
TEST_URI = "mysql+pymysql://root:pass@localhost:3306/digitaliza_test"

_APPLY_CONFIRM_MSG = "--apply requiere --confirm-batch igual a --batch-id."
_MOTIVO_NOTIF = "Carnet de Sanidad"
_MOTIVO_COMP = "Falta de Higiene"
_RUBRO_CANONICO = "Comestibles"


@dataclass(frozen=True)
class PilotSeedMinimo:
    """Datos mínimos únicos por test para import apply determinista."""

    ec5_uuid: str
    batch_id: str
    inspector_nombre: str
    rubro_nombre: str
    documento: str
    odt_numero: str
    legacy_ref_hash: str
    acta_inspeccion: str
    acta_notificacion: str
    acta_comprobacion: str


def _ensure_turno() -> Turno:
    turno = Turno.query.first()
    if turno:
        return turno
    turno = Turno(turno=TipoTurno.MANIANA)
    db.session.add(turno)
    db.session.flush()
    return turno


def _ensure_motivo(nombre: str) -> Motivo:
    motivo = Motivo.query.filter_by(nombre=nombre).first()
    if motivo:
        return motivo
    motivo = Motivo(nombre=nombre)
    db.session.add(motivo)
    db.session.flush()
    return motivo


def _ensure_rubro(nombre: str) -> Rubro:
    rubro = Rubro.query.filter_by(nombre=nombre).first()
    if rubro:
        return rubro
    rubro = Rubro(nombre=nombre)
    db.session.add(rubro)
    db.session.flush()
    return rubro


@pytest.fixture
def pilot_seed_minimo(app) -> PilotSeedMinimo:
    """
    Siembra inspector, rubro y motivos mínimos con identificadores únicos.

    Ejecuta dentro de app.app_context() y hace commit para visibilidad en apply.
    """
    tag = uuid.uuid4().hex[:10]
    ec5 = str(uuid.uuid4())
    legajo = f"p{tag[:4]}".upper()[:5]
    if len(legajo) < 5:
        legajo = legajo.ljust(5, "0")
    seed = PilotSeedMinimo(
        ec5_uuid=ec5,
        batch_id=f"pilot-batch-{tag}",
        inspector_nombre=f"Piloto Inspector {tag}",
        rubro_nombre=_RUBRO_CANONICO,
        documento=f"20{tag[:8]}",
        odt_numero=str(int(tag[:6], 16) % 900000 + 100000),
        legacy_ref_hash=f"legacy-{tag}",
        acta_inspeccion=str(440000 + int(tag[:3], 16) % 999),
        acta_notificacion=str(441000 + int(tag[3:6], 16) % 999),
        acta_comprobacion=str(442000 + int(tag[6:9], 16) % 999),
    )
    with app.app_context():
        turno = _ensure_turno()
        _ensure_rubro(seed.rubro_nombre)
        _ensure_motivo(_MOTIVO_NOTIF)
        _ensure_motivo(_MOTIVO_COMP)
        inspector = Inspector(
            nombre=seed.inspector_nombre,
            legajo=legajo,
            turno_id=turno.id,
        )
        db.session.add(inspector)
        db.session.commit()
    return seed


@pytest.fixture
def pilot_io_dirs(tmp_path: Path) -> Tuple[Path, Path]:
    """repo_root y output_dir hermanos: salida fuera del árbol repo simulado."""
    repo_root = tmp_path / "repo-falso"
    repo_root.mkdir()
    output_dir = tmp_path / "output-seguro"
    return repo_root, output_dir


def test_rechaza_sandbox_test_railway_remoto() -> None:
    with pytest.raises(HistoricoMigracionImportSecurityError):
        validate_migracion_import_database_uri(SANDBOX_URI)
    with pytest.raises(HistoricoMigracionImportSecurityError):
        validate_migracion_import_database_uri(TEST_URI)
    with pytest.raises(HistoricoMigracionImportSecurityError):
        validate_migracion_import_database_uri(
            "mysql+pymysql://u:p@containers-us-west-123.railway.app:3306/digitaliza_migracion"
        )


def test_solo_evidencia_finalizada_es_candidata(tmp_path: Path) -> None:
    path = tmp_path / "ev.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["estado_coincidencia", "ec5_uuid", "legacy_ref_hash"],
        )
        w.writeheader()
        w.writerow(
            {
                "estado_coincidencia": EVID_FINAL,
                "ec5_uuid": "u1",
                "legacy_ref_hash": "abc",
            }
        )
        w.writerow(
            {
                "estado_coincidencia": "EVIDENCIA_SANDBOX_NO_FINALIZADA",
                "ec5_uuid": "u2",
                "legacy_ref_hash": "def",
            }
        )
    _, rows = load_evidence_finalizadas(path)
    assert len(rows) == 1
    assert rows[0]["ec5_uuid"] == "u1"


def _write_min_epi(tmp_path: Path, ec5: str = "uuid-pilot-1") -> Path:
    epi = tmp_path / "epi.csv"
    epi.write_text(
        "ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N,3_Qu_inspectores_con,"
        "4_Domicilio,5_Pudo_realizar_la_i,6_Tipo_de_inspeccin,8_Numero_de_la_Notif,"
        "14_Nombre_de_Fantasa,15_Razn_Socialnombre,16_DNI_del_Contribuy,17_Rubro,"
        "80_Realizo_Acta_de_I,82_Numero_del_Acta_d,84_Realizo_Acta_de_N,86_Numero_del_Acta_d,"
        "87_Infracciones,91_Realizo_Acta_de_C,93_Numero_del_Acta_d,94_Infracciones,"
        "99_Realizo_Acta_de_C,101_Numero_de_Acta_d,103_Realizo_Acta_de_,105_Numero_de_Acta_d,"
        "107_Kilos_Decomisado\n"
        f"{ec5},2024-05-10,100,Accardi José,Mitre 100,SI,Inicial,,"
        "Pan SA,,20123456789,Comestibles,SI,440001,SI,440002,Carnet de Sanidad,"
        "SI,440003,Falta de Higiene,,,,,\n",
        encoding="utf-8",
    )
    return epi


def _write_epi_for_seed(tmp_path: Path, seed: PilotSeedMinimo) -> Path:
    epi = tmp_path / f"epi-{seed.ec5_uuid}.csv"
    epi.write_text(
        "ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N,3_Qu_inspectores_con,"
        "4_Domicilio,5_Pudo_realizar_la_i,6_Tipo_de_inspeccin,8_Numero_de_la_Notif,"
        "14_Nombre_de_Fantasa,15_Razn_Socialnombre,16_DNI_del_Contribuy,17_Rubro,"
        "80_Realizo_Acta_de_I,82_Numero_del_Acta_d,84_Realizo_Acta_de_N,86_Numero_del_Acta_d,"
        "87_Infracciones,91_Realizo_Acta_de_C,93_Numero_del_Acta_d,94_Infracciones,"
        "99_Realizo_Acta_de_C,101_Numero_de_Acta_d,103_Realizo_Acta_de_,105_Numero_de_Acta_d,"
        "107_Kilos_Decomisado\n"
        f"{seed.ec5_uuid},2024-05-10,{seed.odt_numero},{seed.inspector_nombre},Mitre 100,SI,Inicial,,"
        f"Pan SA,,{seed.documento},{seed.rubro_nombre},SI,{seed.acta_inspeccion},SI,"
        f"{seed.acta_notificacion},{_MOTIVO_NOTIF},SI,{seed.acta_comprobacion},{_MOTIVO_COMP},"
        ",,,,\n",
        encoding="utf-8",
    )
    return epi


def _write_evidence(tmp_path: Path, ec5: str = "uuid-pilot-1", legacy_ref_hash: str = "hash1") -> Path:
    ev = tmp_path / "ev.csv"
    with ev.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["estado_coincidencia", "ec5_uuid", "legacy_ref_hash"],
        )
        w.writeheader()
        w.writerow(
            {
                "estado_coincidencia": EVID_FINAL,
                "ec5_uuid": ec5,
                "legacy_ref_hash": legacy_ref_hash,
            }
        )
    return ev


def _write_evidence_for_seed(tmp_path: Path, seed: PilotSeedMinimo) -> Path:
    return _write_evidence(tmp_path, seed.ec5_uuid, seed.legacy_ref_hash)


def _target() -> MigracionImportTarget:
    return validate_migracion_import_database_uri(MIGRACION_URI)


def _test_db_target() -> MigracionImportTarget:
    return MigracionImportTarget(
        driver="mysql+pymysql",
        host="localhost",
        port=3306,
        database="digitaliza_test",
    )


def test_dry_run_no_escribe(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    repo_root, output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        before = count_operational_tables()
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id="batch-dry",
            cutoff=date(2026, 10, 1),
            dry_run=True,
            apply=False,
            confirm_batch=None,
            target=_test_db_target(),
            repo_root=repo_root,
        )
        after = count_operational_tables()
    assert before == after
    assert (output_dir / "resumen_piloto_importacion.json").exists()


def test_salida_dentro_de_repo_rechazada(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    repo_root, _output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        with pytest.raises(ValueError, match="dentro del repositorio"):
            run_pilot_import(
                output_dir=repo_root / "salida-invalida",
                epicollect_csv=epi,
                sandbox_evidence_csv=ev,
                batch_id="batch-in",
                cutoff=date(2026, 10, 1),
                dry_run=True,
                apply=False,
                confirm_batch=None,
                target=_test_db_target(),
                repo_root=repo_root,
            )


def test_apply_sin_confirmacion_rechazado(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    repo_root, output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        with pytest.raises(ValueError, match=_APPLY_CONFIRM_MSG):
            run_pilot_import(
                output_dir=output_dir,
                epicollect_csv=epi,
                sandbox_evidence_csv=ev,
                batch_id="b1",
                cutoff=date(2026, 10, 1),
                dry_run=False,
                apply=True,
                confirm_batch=None,
                target=_test_db_target(),
                repo_root=repo_root,
            )
        with pytest.raises(ValueError, match=_APPLY_CONFIRM_MSG):
            run_pilot_import(
                output_dir=output_dir,
                epicollect_csv=epi,
                sandbox_evidence_csv=ev,
                batch_id="b1",
                cutoff=date(2026, 10, 1),
                dry_run=False,
                apply=True,
                confirm_batch="otro",
                target=_test_db_target(),
                repo_root=repo_root,
            )


def test_inspector_no_resoluble_revisar(app, tmp_path: Path) -> None:
    from app.domains.migracion_historica.epicollect_actas_inventario import (
        _header_indices,
        extract_row_snapshot,
    )

    epi = tmp_path / "epi.csv"
    epi.write_text(
        "ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N,3_Qu_inspectores_con,17_Rubro,"
        "4_Domicilio,16_DNI_del_Contribuy,84_Realizo_Acta_de_N,86_Numero_del_Acta_d,87_Infracciones\n"
        "u1,2024-01-01,1,Inspector Inexistente,Comestibles,Mitre 10,20111111111,SI,1,Carnet de Sanidad\n",
        encoding="utf-8",
    )
    with epi.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        hdr = next(reader)
        row = next(reader)
    by_name = _header_indices(hdr)
    snap = extract_row_snapshot(row, hdr, by_name)
    ev_rows = [
        {
            "estado_coincidencia": EVID_FINAL,
            "ec5_uuid": "u1",
            "legacy_ref_hash": "h",
        }
    ]
    with app.app_context():
        plans = build_plan_from_sources(
            ev_rows,
            {"u1": snap},
            {"u1": row},
            {"u1": hdr},
            date(2026, 10, 1),
        )
    assert plans[0].decision == DECISION_REVISAR
    assert plans[0].motivo_revision == "inspector_no_resoluble"


def test_resumen_sin_pii(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    repo_root, output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id="batch-pii",
            cutoff=date(2026, 10, 1),
            dry_run=True,
            apply=False,
            confirm_batch=None,
            target=_test_db_target(),
            repo_root=repo_root,
        )
    blob = (output_dir / "resumen_piloto_importacion.json").read_text(encoding="utf-8")
    assert "20123456789" not in blob
    assert "http" not in blob.lower()
    assert "secret" not in blob.lower()
    assert "pass@" not in blob.lower()
    data = json.loads(blob)
    assert data["conexion_verificada"] is True
    assert data["database_destino_efectiva"] == "digitaliza_test"


def test_uri_migracion_con_sesion_test_aborta_sin_escribir(
    app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]
) -> None:
    """Reproduce incidente: URI declara migracion pero la sesión está en digitaliza_test."""
    repo_root, output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        before = count_operational_tables()
        with pytest.raises(MigracionTargetConnectionError, match="digitaliza_test"):
            run_pilot_import(
                output_dir=output_dir,
                epicollect_csv=epi,
                sandbox_evidence_csv=ev,
                batch_id="batch-mismatch",
                cutoff=date(2026, 10, 1),
                dry_run=True,
                apply=False,
                confirm_batch=None,
                target=_target(),
                repo_root=repo_root,
            )
        assert count_operational_tables() == before
    assert not (output_dir / "resumen_piloto_importacion.json").exists()


def test_pin_explicit_uri_prevalece_sobre_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SANDBOX_URI)
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", SANDBOX_URI)
    pinned = pin_explicit_database_uri(MIGRACION_URI)
    assert pinned == MIGRACION_URI
    assert os.environ.get("SQLALCHEMY_DATABASE_URI") == MIGRACION_URI
    assert "DATABASE_URL" not in os.environ


def test_cli_rechaza_uri_sandbox(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sys.argv = [
        str(SCRIPT),
        "--database-uri",
        SANDBOX_URI,
        "--epicollect-csv",
        str(tmp_path / "e.csv"),
        "--sandbox-evidence-csv",
        str(tmp_path / "v.csv"),
        "--batch-id",
        "x",
        "--output",
        str(tmp_path / "o"),
    ]
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc.value.code == 2
    assert "mysql+pymysql" not in capsys.readouterr().err


def test_apply_crea_notificacion_y_comprobacion(
    app,
    tmp_path: Path,
    pilot_io_dirs: Tuple[Path, Path],
    pilot_seed_minimo: PilotSeedMinimo,
) -> None:
    repo_root, output_dir = pilot_io_dirs
    seed = pilot_seed_minimo
    epi = _write_epi_for_seed(tmp_path, seed)
    ev = _write_evidence_for_seed(tmp_path, seed)
    with app.app_context():
        rutas_antes = db.session.query(RutaTrabajo).count()
        items_antes = db.session.query(RutaItem).count()
        iniciadores_antes = db.session.query(IniciadorRuta).count()
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id=seed.batch_id,
            cutoff=date(2026, 10, 1),
            dry_run=False,
            apply=True,
            confirm_batch=seed.batch_id,
            target=_test_db_target(),
            repo_root=repo_root,
        )
        act = Actuaciones.query.filter_by(ec5_uuid=seed.ec5_uuid).one()
        assert act.notificacion_id is not None
        assert act.comprobacion_id is not None
        assert db.session.query(RutaTrabajo).count() == rutas_antes
        assert db.session.query(RutaItem).count() == items_antes
        assert db.session.query(IniciadorRuta).count() == iniciadores_antes


def test_idempotencia_segundo_apply(
    app,
    tmp_path: Path,
    pilot_io_dirs: Tuple[Path, Path],
    pilot_seed_minimo: PilotSeedMinimo,
) -> None:
    repo_root, output_dir = pilot_io_dirs
    seed = pilot_seed_minimo
    epi = _write_epi_for_seed(tmp_path, seed)
    ev = _write_evidence_for_seed(tmp_path, seed)
    kwargs = dict(
        output_dir=output_dir,
        epicollect_csv=epi,
        sandbox_evidence_csv=ev,
        batch_id=seed.batch_id,
        cutoff=date(2026, 10, 1),
        dry_run=False,
        apply=True,
        confirm_batch=seed.batch_id,
        target=_test_db_target(),
        repo_root=repo_root,
    )
    with app.app_context():
        actuaciones_antes = Actuaciones.query.count()
        registros_antes = MigracionHistoricaRegistro.query.count()
        orden_trabajo_antes = OrdenTrabajo.query.count()

        r1 = run_pilot_import(**kwargs)
        assert r1.resumen["insertadas"] == 1
        assert r1.resumen["omitidas_idempotencia"] == 0

        act = Actuaciones.query.filter_by(ec5_uuid=seed.ec5_uuid).one()
        assert Actuaciones.query.count() == actuaciones_antes + 1

        registro = (
            MigracionHistoricaRegistro.query.filter_by(
                source_name=SOURCE_NAME,
                source_record_uuid=seed.ec5_uuid,
            ).one()
        )
        assert registro.decision == DECISION_INSERTED
        assert registro.target_actuacion_id == act.id
        assert MigracionHistoricaRegistro.query.count() == registros_antes + 1
        orden_trabajo_tras_primera = OrdenTrabajo.query.count()
        assert orden_trabajo_tras_primera == orden_trabajo_antes + 1

        r2 = run_pilot_import(**kwargs)
        assert r2.resumen["insertadas"] == 0
        assert r2.resumen["omitidas_idempotencia"] == 1

        assert Actuaciones.query.filter_by(ec5_uuid=seed.ec5_uuid).count() == 1
        assert Actuaciones.query.count() == actuaciones_antes + 1
        assert MigracionHistoricaRegistro.query.count() == registros_antes + 1
        assert OrdenTrabajo.query.count() == orden_trabajo_tras_primera

        registro_despues = (
            MigracionHistoricaRegistro.query.filter_by(
                source_name=SOURCE_NAME,
                source_record_uuid=seed.ec5_uuid,
            ).one()
        )
        assert registro_despues.id == registro.id
        assert registro_despues.target_actuacion_id == act.id
        assert registro_despues.decision == DECISION_INSERTED


def test_falla_revierte_cadena(
    app,
    tmp_path: Path,
    pilot_io_dirs: Tuple[Path, Path],
    pilot_seed_minimo: PilotSeedMinimo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, output_dir = pilot_io_dirs
    seed = pilot_seed_minimo
    epi = _write_epi_for_seed(tmp_path, seed)
    ev = _write_evidence_for_seed(tmp_path, seed)

    with app.app_context():

        def _boom(plan):  # noqa: ANN001
            raise ValueError("fallo_simulado")

        monkeypatch.setattr(
            "app.domains.migracion_historica.historico_piloto_import_service._import_single_chain",
            lambda plan: _boom(plan),
        )
        before = Actuaciones.query.count()
        run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id=seed.batch_id,
            cutoff=date(2026, 10, 1),
            dry_run=False,
            apply=True,
            confirm_batch=seed.batch_id,
            target=_test_db_target(),
            repo_root=repo_root,
        )
        assert Actuaciones.query.count() == before
        assert not Actuaciones.query.filter_by(ec5_uuid=seed.ec5_uuid).first()


def test_migracion_registro_revision_en_cadena() -> None:
    path = BACKEND_ROOT / "migrations" / "versions" / "a2b3c4d5e6f8_migracion_historica_registro.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision = "a2b3c4d5e6f8"' in text
    assert 'down_revision = "z1a2b3c4d5e6"' in text
    assert "migracion_historica_registro" in text


def test_conteos_resumen_coherentes(app, tmp_path: Path, pilot_io_dirs: Tuple[Path, Path]) -> None:
    repo_root, output_dir = pilot_io_dirs
    epi = _write_min_epi(tmp_path)
    ev = _write_evidence(tmp_path)
    with app.app_context():
        result = run_pilot_import(
            output_dir=output_dir,
            epicollect_csv=epi,
            sandbox_evidence_csv=ev,
            batch_id="c-batch",
            cutoff=date(2026, 10, 1),
            dry_run=True,
            apply=False,
            confirm_batch=None,
            target=_test_db_target(),
            repo_root=repo_root,
        )
        resumen = result.resumen
        assert resumen["conteos_antes"] == resumen["conteos_despues"]
        rutas = resumen["conteos_rutas_iniciadores"]
        assert rutas["ruta_item"] == resumen["conteos_despues"]["ruta_item"]
        assert rutas["ruta_trabajo"] == resumen["conteos_despues"]["ruta_trabajo"]
        assert rutas["iniciador_ruta"] == resumen["conteos_despues"]["iniciador_ruta"]
