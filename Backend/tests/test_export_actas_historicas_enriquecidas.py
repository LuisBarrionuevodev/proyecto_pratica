"""Tests export enriquecido MySQL histórico (V1.1-MIG-ACTAS.0C)."""

from __future__ import annotations

import json
import runpy
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.domains.migracion_historica.historico_actas_enriquecido_export import (
    EXPORT_CSV_COLUMNS,
    actuacion_to_export_row,
    export_actas_historicas_enriquecidas,
    legacy_ref_hash_for_actuacion,
    write_enriquecido_outputs,
)
from app.domains.migracion_historica.historico_sandbox_export_security import (
    HistoricoExportSecurityError,
    validate_sandbox_export_database_uri,
)
from app.domains.migracion_historica.epicollect_actas_inventario import (
    assert_output_outside_repo,
    resolve_repo_root,
)
BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND_ROOT / "scripts" / "export_actas_historicas_enriquecidas.py"
SANDBOX_URI = "mysql+pymysql://root:secret@127.0.0.1:3306/digitaliza_sandbox"


def test_rechaza_uri_remota_railway_y_test() -> None:
    with pytest.raises(HistoricoExportSecurityError):
        validate_sandbox_export_database_uri(
            "mysql+pymysql://u:p@containers-us-west-123.railway.app:3306/digitaliza_sandbox"
        )
    with pytest.raises(HistoricoExportSecurityError):
        validate_sandbox_export_database_uri(
            "mysql+pymysql://u:p@localhost:3306/digitaliza_test"
        )
    with pytest.raises(HistoricoExportSecurityError):
        validate_sandbox_export_database_uri(
            "mysql+pymysql://u:p@localhost:3306/digitaliza_pilot"
        )


def test_rechaza_salida_dentro_repo() -> None:
    repo = resolve_repo_root(BACKEND_ROOT)
    with pytest.raises(ValueError, match="dentro del repositorio"):
        assert_output_outside_repo(repo / "export_out", repo)


def test_cli_stdout_sin_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out"
    fake = SimpleNamespace(total_exportadas=1, csv_sha256="a" * 64)

    def _fake_export(output_dir: Path, database_uri=None, repo_root=None):  # noqa: ARG001
        return fake

    monkeypatch.setattr(
        "app.domains.migracion_historica.historico_actas_enriquecido_export.export_actas_historicas_enriquecidas",
        _fake_export,
    )
    sys.argv = [str(SCRIPT), "--output", str(out)]
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc.value.code == 0
    combined = capsys.readouterr().out + capsys.readouterr().err
    assert "secret" not in combined.lower()
    assert "mysql+pymysql" not in combined


def _build_actuacion_full() -> MagicMock:
    act = MagicMock()
    act.id = 42
    act.fecha = date(2026, 5, 10)
    act.mes = 5
    act.anio = 2026
    act.tipo = "INSPECCION"
    act.carga_solo_comprobacion = False
    act.ec5_uuid = None
    act.contraproducencia = None
    act.realizo_nueva_inspeccion = None
    act.resultado_cumplimiento_oficio = None
    act.nombre_local = ""
    act.titular_nombre_historico = None
    act.titular_apellido_historico = None
    act.titular_razon_social_historica = None
    act.orden_trabajo = SimpleNamespace(numero_acta="003074", anio=2026)
    act.notificacion = SimpleNamespace(
        numero_acta="004001",
        anio=2026,
        fecha_notificacion=date(2026, 5, 10),
        plazo_dias=5,
        fecha_vencimiento=date(2026, 5, 15),
        motivos=[SimpleNamespace(nombre="Higiene", id=1)],
    )
    act.comprobacion = SimpleNamespace(numero_acta="005001", anio=2026, motivo="Grave", expediente=[], oficio=[])
    act.inspeccion = SimpleNamespace(numero_acta="004415", anio=2026)
    act.clausura = None
    act.decomiso = None
    contrib = SimpleNamespace(documento="20123456789", nombre="Juan", apellido="Perez", razon_social="")
    act.domicilio = SimpleNamespace(
        calle="Mitre",
        numero="100",
        numero_tipo="",
        ciudad="SMT",
        cp="4000",
        contribuyente=contrib,
    )
    act.inspector = [SimpleNamespace(nombre="Inspector Uno")]
    row = actuacion_to_export_row(act)
    assert row["notificacion_numero"] == "004001"
    assert row["comprobacion_numero"] == "005001"
    assert row["inspeccion_numero"] == "004415"
    return act


def test_actuacion_con_notificacion_y_comprobacion() -> None:
    _build_actuacion_full()


def test_clausura_y_decomiso_en_fila() -> None:
    act = MagicMock()
    act.id = 7
    act.fecha = date(2026, 1, 1)
    act.mes = 1
    act.anio = 2026
    act.tipo = None
    act.carga_solo_comprobacion = False
    act.ec5_uuid = None
    act.contraproducencia = None
    act.realizo_nueva_inspeccion = None
    act.resultado_cumplimiento_oficio = None
    act.nombre_local = ""
    act.orden_trabajo = None
    act.notificacion = None
    act.comprobacion = None
    act.inspeccion = None
    act.domicilio = None
    act.inspector = []
    act.titular_nombre_historico = None
    act.titular_apellido_historico = None
    act.titular_razon_social_historica = None
    act.clausura = SimpleNamespace(numero_acta="000101", anio=2026)
    act.decomiso = SimpleNamespace(numero_acta="000202", anio=2026, cantidad=Decimal("12.5"))
    row = actuacion_to_export_row(act)
    assert row["clausura_numero"] == "000101"
    assert row["decomiso_kilos"] == "12.5"


def test_pii_solo_en_csv_local(tmp_path: Path) -> None:
    act = _build_actuacion_full()
    row = actuacion_to_export_row(act)
    target = validate_sandbox_export_database_uri(SANDBOX_URI)
    result = write_enriquecido_outputs([row], tmp_path, target, ["campo_x"])
    csv_text = result.csv_path.read_text(encoding="utf-8")
    assert "20123456789" in csv_text
    resumen = json.loads(result.resumen_path.read_text(encoding="utf-8"))
    blob = json.dumps(resumen)
    assert "20123456789" not in blob
    assert "Juan" not in blob
    assert "Mitre" not in blob


def test_resumen_sin_media_ni_urls(tmp_path: Path) -> None:
    act = _build_actuacion_full()
    row = actuacion_to_export_row(act)
    target = validate_sandbox_export_database_uri(SANDBOX_URI)
    write_enriquecido_outputs([row], tmp_path, target, [])
    resumen = json.loads((tmp_path / "resumen_export_actas_historicas_enriquecido.json").read_text())
    assert resumen["media_urls_exportadas"] is False
    assert "http" not in json.dumps(resumen).lower()


def test_export_no_escribe_en_db(tmp_path: Path) -> None:
    act = _build_actuacion_full()
    session = MagicMock()
    session.query.return_value.options.return_value.order_by.return_value.all.return_value = [act]

    class _SessionCtx:
        def __enter__(self):
            return session

        def __exit__(self, *args):  # noqa: ARG002
            return False

    with patch(
        "app.domains.migracion_historica.historico_actas_enriquecido_export.create_engine"
    ) as mock_engine:
        mock_engine.return_value = MagicMock()
        with patch(
            "app.domains.migracion_historica.historico_actas_enriquecido_export.Session",
            return_value=_SessionCtx(),
        ):
                with patch(
                    "app.domains.migracion_historica.historico_actas_enriquecido_export.resolve_export_database_uri",
                    return_value=SANDBOX_URI,
                ):
                    with patch(
                        "app.domains.migracion_historica.historico_actas_enriquecido_export._install_readonly_guard"
                    ):
                        export_actas_historicas_enriquecidas(tmp_path, database_uri=SANDBOX_URI)
    session.commit.assert_not_called()
    session.add.assert_not_called()


def test_legacy_ref_hash_estable() -> None:
    h1 = legacy_ref_hash_for_actuacion(99)
    h2 = legacy_ref_hash_for_actuacion(99)
    h3 = legacy_ref_hash_for_actuacion(100)
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 24


def test_csv_no_incluye_columnas_media() -> None:
    cols = set(EXPORT_CSV_COLUMNS)
    assert "url" not in cols
    assert "foto" not in {c.lower() for c in cols}


# --- V1.1-MIG-ACTAS.0C.1 evidencia sandbox por ODT ---

from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (  # noqa: E402
    ESTADO_COINCIDENCIA_OT_AMBIGUA,
    ESTADO_COINCIDENCIA_OT_UNICA,
    ESTADO_CONFLICTO_IDENTIDAD,
    ESTADO_EPI_SIN_OT,
    ESTADO_EVIDENCIA_FINALIZADA,
    ESTADO_EVIDENCIA_NO_FINALIZADA,
    EpiOdtRow,
    SandboxOdtCandidate,
    clasificar_por_odt,
    export_evidencia_sandbox_por_odt,
    normalize_odt,
    write_odt_evidencia_outputs,
)
from app.domains.migracion_historica.historico_sandbox_export_security import (
    validate_sandbox_export_database_uri,
)


def _epi_snap(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(
        ec5_uuid=kwargs.get("ec5_uuid", "epi-uuid-1"),
        fecha_inspec=kwargs.get("fecha", date(2024, 6, 15)),
        tipo_inspeccion=kwargs.get("tipo", "Inicial"),
        doc_norm=kwargs.get("doc", ""),
        dom_norm=kwargs.get("dom", ""),
        titular_norm=kwargs.get("tit", ""),
    )


def _sandbox_cand(
    act_id: int,
    odt: str,
    anio: int,
    doc: str = "",
    dom: str = "",
    tit: str = "",
    ruta_items: list | None = None,
) -> SandboxOdtCandidate:
    act = MagicMock()
    act.id = act_id
    act.fecha = date(anio, 6, 15)
    act.tipo = "INSPECCION"
    act.notificacion = None
    act.comprobacion = None
    act.clausura = None
    act.decomiso = None
    act.orden_trabajo = SimpleNamespace(numero_acta=odt, anio=anio)
    return SandboxOdtCandidate(
        act=act,
        odt_norm=normalize_odt(odt),
        odt_anio=anio,
        doc_norm=doc,
        dom_norm=dom,
        titular_norm=tit,
        ruta_items=ruta_items or [],
    )


def test_odt_anio_unico_epicollect_sandbox() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(doc="20111111111"), odt_norm="003074", odt_anio=2024)]
    sb = [_sandbox_cand(1, "003074", 2024, doc="20111111111")]
    cls, desc = clasificar_por_odt(epi, sb)
    assert desc == 0
    assert cls[0].estado == ESTADO_EVIDENCIA_NO_FINALIZADA


def test_odt_ceros_significativos() -> None:
    assert normalize_odt(" 003-074 ") == "003074"
    epi = [EpiOdtRow(snap=_epi_snap(doc="20999999999"), odt_norm="003074", odt_anio=2025)]
    sb = [_sandbox_cand(2, "003074", 2025, doc="20999999999")]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado in (
        ESTADO_EVIDENCIA_NO_FINALIZADA,
        ESTADO_EVIDENCIA_FINALIZADA,
        ESTADO_COINCIDENCIA_OT_UNICA,
    )


def test_odt_duplicada_epicollect_ambigua() -> None:
    snap1 = _epi_snap(ec5_uuid="a")
    snap2 = _epi_snap(ec5_uuid="b")
    epi = [
        EpiOdtRow(snap=snap1, odt_norm="100", odt_anio=2023),
        EpiOdtRow(snap=snap2, odt_norm="100", odt_anio=2023),
    ]
    sb = [_sandbox_cand(3, "100", 2023, doc="20123456789")]
    cls, _ = clasificar_por_odt(epi, sb)
    assert all(c.estado == ESTADO_COINCIDENCIA_OT_AMBIGUA for c in cls)


def test_dos_sandbox_misma_odt_ambigua() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(), odt_norm="200", odt_anio=2022)]
    sb = [
        _sandbox_cand(4, "200", 2022, doc="20111111111"),
        _sandbox_cand(5, "200", 2022, doc="20222222222"),
    ]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_COINCIDENCIA_OT_AMBIGUA


def test_sandbox_sin_epicollect_descartada() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(), odt_norm="300", odt_anio=2021)]
    sb = [
        _sandbox_cand(6, "300", 2021, doc="20111111111"),
        _sandbox_cand(7, "999", 2021, doc="20111111111"),
    ]
    _, desc = clasificar_por_odt(epi, sb)
    assert desc == 1


def test_documento_diferente_conflicto_identidad() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(doc="20111111111"), odt_norm="400", odt_anio=2020)]
    sb = [_sandbox_cand(8, "400", 2020, doc="20999999999")]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_CONFLICTO_IDENTIDAD


def test_domicilio_titular_sin_documento_compatible() -> None:
    dom = "MITRE 100 SMT"
    from app.domains.migracion_historica.epicollect_cadenas_historicas import (
        normalize_domicilio,
        normalize_persona_razon,
    )

    dom_n = normalize_domicilio(dom)
    tit_n = normalize_persona_razon("Panaderia Lopez")
    epi = [EpiOdtRow(snap=_epi_snap(dom=dom_n, tit=tit_n), odt_norm="500", odt_anio=2019)]
    sb = [_sandbox_cand(9, "500", 2019, dom=dom_n, tit=tit_n)]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_EVIDENCIA_NO_FINALIZADA


def test_estado_finalizado_evidencia_finalizada() -> None:
    ri = SimpleNamespace(estado_ruta_item="FINALIZADO", estado_ejecucion=None)
    epi = [EpiOdtRow(snap=_epi_snap(doc="20101010101"), odt_norm="600", odt_anio=2018)]
    sb = [_sandbox_cand(10, "600", 2018, doc="20101010101", ruta_items=[ri])]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_EVIDENCIA_FINALIZADA


def test_estado_no_finalizado() -> None:
    ri = SimpleNamespace(estado_ruta_item="EN_PROCESO", estado_ejecucion=None)
    epi = [EpiOdtRow(snap=_epi_snap(doc="20101010102"), odt_norm="700", odt_anio=2017)]
    sb = [_sandbox_cand(11, "700", 2017, doc="20101010102", ruta_items=[ri])]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_EVIDENCIA_NO_FINALIZADA


def test_epi_sin_ot_valida() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(), odt_norm="", odt_anio=2016)]
    cls, _ = clasificar_por_odt(epi, [])
    assert cls[0].estado == ESTADO_EPI_SIN_OT


def test_identidad_insuficiente_queda_coincidencia_unica() -> None:
    epi = [EpiOdtRow(snap=_epi_snap(), odt_norm="800", odt_anio=2015)]
    sb = [_sandbox_cand(12, "800", 2015)]
    cls, _ = clasificar_por_odt(epi, sb)
    assert cls[0].estado == ESTADO_COINCIDENCIA_OT_UNICA


def test_odt_export_sin_pii_en_json_ni_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = validate_sandbox_export_database_uri(SANDBOX_URI)
    resumen = {
        "modo": "EVIDENCIA_SANDBOX_FILTRADA_ODT",
        "database": target.database,
        "host": target.host,
        "port": target.port,
        "epicollect_sha256": "a" * 64,
        "evidencias_finalizadas": 0,
        "coincidencias_ambiguas": 0,
        "sandbox_descartadas_no_en_epicollect": 0,
        "media_urls_exportadas": False,
    }
    write_odt_evidencia_outputs([], resumen, tmp_path, target)
    blob = (tmp_path / "resumen_evidencia_sandbox_odt.json").read_text(encoding="utf-8")
    assert "20123456789" not in blob
    assert "http" not in blob.lower()

    def _fake_export(*args, **kwargs):  # noqa: ARG001
        write_odt_evidencia_outputs([], resumen, kwargs.get("output_dir") or args[0], target)
        from app.domains.migracion_historica.historico_sandbox_odt_evidencia import (
            SandboxOdtExportResult,
        )

        return SandboxOdtExportResult(
            evidencia_csv_path=tmp_path / "evidencia_sandbox_por_odt.csv",
            revisar_csv_path=tmp_path / "revisar_coincidencias_ot.csv",
            resumen_path=tmp_path / "resumen_evidencia_sandbox_odt.json",
            resumen=resumen,
            target=target,
        )

    monkeypatch.setattr(
        "app.domains.migracion_historica.historico_sandbox_odt_evidencia.export_evidencia_sandbox_por_odt",
        _fake_export,
    )
    epi = tmp_path / "epi.csv"
    epi.write_text("ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N\n", encoding="utf-8")
    sys.argv = [
        str(SCRIPT),
        "--output",
        str(tmp_path / "out"),
        "--epicollect-csv",
        str(epi),
    ]
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc.value.code == 0
    combined = capsys.readouterr().out + capsys.readouterr().err
    assert "mysql+pymysql" not in combined
    assert "secret" not in combined.lower()


def test_export_odt_no_escribe_en_db(tmp_path: Path) -> None:
    epi_csv = tmp_path / "epi.csv"
    epi_csv.write_text(
        "ec5_uuid,1_Fecha_de_la_inspec,2_Orden_de_Trabajo_N,6_Tipo_de_inspeccin,"
        "4_Domicilio,16_DNI_del_Contribuy,14_Nombre_de_Fantasa,15_Razn_Socialnombre\n"
        "u1,2024-01-01,100,Inicial,,20111111111,,\n",
        encoding="utf-8",
    )
    act = _build_actuacion_full()
    session = MagicMock()
    session.query.return_value.options.return_value.order_by.return_value.all.return_value = [act]
    session.query.return_value.filter.return_value.all.return_value = []

    class _SessionCtx:
        def __enter__(self):
            return session

        def __exit__(self, *args):  # noqa: ARG002
            return False

    out = tmp_path / "export_odt"
    with patch(
        "app.domains.migracion_historica.historico_sandbox_odt_evidencia.create_engine"
    ) as mock_engine:
        mock_engine.return_value = MagicMock()
        with patch(
            "app.domains.migracion_historica.historico_sandbox_odt_evidencia.Session",
            return_value=_SessionCtx(),
        ):
            with patch(
                "app.domains.migracion_historica.historico_sandbox_odt_evidencia.resolve_export_database_uri",
                return_value=SANDBOX_URI,
            ):
                with patch(
                    "app.domains.migracion_historica.historico_sandbox_odt_evidencia._install_readonly_guard"
                ):
                    export_evidencia_sandbox_por_odt(
                        out,
                        epi_csv,
                        date(2026, 10, 1),
                        database_uri=SANDBOX_URI,
                        repo_root=BACKEND_ROOT.parent,
                    )
    session.commit.assert_not_called()
    session.add.assert_not_called()
