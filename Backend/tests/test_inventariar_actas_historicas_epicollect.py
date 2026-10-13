"""Tests del inventario read-only EpiCollect (V1.1-MIG-ACTAS.0)."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from app.domains.migracion_historica.epicollect_actas_inventario import (
    ALLOWED_LOGICAL_COLUMNS,
    Decision,
    assert_output_outside_repo,
    extract_row_snapshot,
    inventariar_csv,
    parse_inspection_date,
    resolve_repo_root,
    snapshot_to_output_row,
    write_inventario_outputs,
    _header_indices,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND_ROOT / "scripts" / "inventariar_actas_historicas_epicollect.py"


def _minimal_header() -> list[str]:
    return [
        "ec5_uuid",
        "1_Fecha_de_la_inspec",
        "2_Orden_de_Trabajo_N",
        "3_Qu_inspectores_con",
        "4_Domicilio",
        "5_Pudo_realizar_la_i",
        "6_Tipo_de_inspeccin",
        "8_Numero_de_la_Notif",
        "80_Realizo_Acta_de_I",
        "82_Numero_del_Acta_d",
        "84_Realizo_Acta_de_N",
        "86_Numero_del_Acta_d",
        "91_Realizo_Acta_de_C",
        "93_Numero_del_Acta_d",
        "99_Realizo_Acta_de_C",
        "101_Numero_de_Acta_d",
        "103_Realizo_Acta_de_",
        "105_Numero_de_Acta_d",
        "107_Kilos_Decomisado",
        "108_Realizo_Desnatur",
        "115_Pego_Faja_de_Cla",
        "117_Numero_de_Expedi",
        "118_Ao",
        "119_Numero_de_Oficio",
        "251_Porque_no_realiz",
        "9_Foto_de_la_Notific",
        "88_Foto_de_la_Notifi",
    ]


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_minimal_header())
        for row in rows:
            w.writerow(row)


def _row_base(
    uuid: str,
    fecha: str,
    tipo: str = "Inspección Integral o Denuncia",
    pudo: str = "SI",
    dom: str = "Calle 123",
    inspeccion: str = "SI",
    num_ins: str = "1001",
    notif: str = "NO",
    num_not: str = "",
    comp: str = "NO",
    num_comp: str = "",
    ref_notif: str = "",
) -> list[str]:
    return [
        uuid,
        fecha,
        "ODT-1",
        "Inspector A",
        dom,
        pudo,
        tipo,
        ref_notif,
        inspeccion,
        num_ins,
        notif,
        num_not,
        comp,
        num_comp,
        "NO",
        "",
        "NO",
        "",
        "",
        "NO",
        "NO",
        "",
        "",
        "",
        "",
        "",
        "",
    ]


def test_fecha_corte_incluye_30_09_excluye_01_10(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    _write_csv(
        csv_path,
        [
            _row_base("u1", "30/09/2026"),
            _row_base("u2", "2026-10-01"),
        ],
    )
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    by_uuid = {s.ec5_uuid: s.decision for s in result.filas}
    assert by_uuid["u1"] != Decision.EXCLUIR_POST_CORTE
    assert by_uuid["u2"] == Decision.EXCLUIR_POST_CORTE


def test_parse_fecha_formatos() -> None:
    d1, f1 = parse_inspection_date("30/09/2026")
    d2, f2 = parse_inspection_date("2026-09-30")
    assert d1 == date(2026, 9, 30) and f1 == "DD/MM/YYYY"
    assert d2 == date(2026, 9, 30) and f2 == "YYYY-MM-DD"


def test_notificacion_y_comprobacion_misma_actuacion(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    row = _row_base("u-both", "2026-09-01")
    row[10] = "SI"
    row[11] = "2002"
    row[12] = "SI"
    row[13] = "3003"
    _write_csv(csv_path, [row])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    assert result.filas[0].decision == Decision.CANDIDATA_CON_AMBAS_ACTAS


def test_clausura_decomiso_con_comprobacion(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    row = _row_base("u-cd", "2026-09-01", comp="SI", num_comp="4004")
    row[14] = "SI"
    row[15] = "5005"
    row[16] = "SI"
    row[17] = "6006"
    row[18] = "12"
    row[19] = "SI"
    row[20] = "SI"
    _write_csv(csv_path, [row])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    snap = result.filas[0]
    assert snap.acta_comprobacion_num == "4004"
    assert snap.acta_clausura_num == "5005"
    assert snap.acta_decomiso_num == "6006"
    assert snap.kilos_decomiso == "12"


def test_reinspeccion_referencia_unica(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    origen = _row_base("origen", "2026-08-01", notif="SI", num_not="9001")
    rein = _row_base(
        "rein",
        "2026-09-15",
        tipo="Reinspección por Notificación",
        ref_notif="9001",
        inspeccion="SI",
        num_ins="9100",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    rein_snap = next(s for s in result.filas if s.ec5_uuid == "rein")
    assert rein_snap.decision == Decision.CANDIDATA_REINSPECCION_NOTIFICACION
    assert rein_snap.previa_ec5_uuid == "origen"


def test_reinspeccion_sin_referencia_o_duplicada_revisar(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    dup1 = _row_base("d1", "2026-08-01", notif="SI", num_not="7777")
    dup2 = _row_base("d2", "2026-08-02", notif="SI", num_not="7777")
    rein_sin = _row_base(
        "r0",
        "2026-09-01",
        tipo="Reinspección por Notificación",
        ref_notif="",
        inspeccion="SI",
        num_ins="1",
    )
    rein_amb = _row_base(
        "r1",
        "2026-09-02",
        tipo="Reinspección por Notificación",
        ref_notif="7777",
        inspeccion="SI",
        num_ins="2",
    )
    _write_csv(csv_path, [dup1, dup2, rein_sin, rein_amb])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    decisions = {s.ec5_uuid: s.decision for s in result.filas}
    assert decisions["r0"] == Decision.REVISAR
    assert decisions["r1"] == Decision.REVISAR


def test_columnas_foto_ignoradas_en_salida(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    row = _row_base("u-foto", "2026-09-01")
    row += ["https://evil.example/photo.jpg", "http://more.example/x"]
    _write_csv(csv_path, [row])
    out = tmp_path / "out"
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    write_inventario_outputs(result, out)
    text = (out / "candidatas_actuaciones_historicas.csv").read_text(encoding="utf-8")
    assert "http" not in text
    assert "Foto" not in text
    out_row = snapshot_to_output_row(result.filas[0])
    assert "http" not in json.dumps(out_row)


def test_salida_dentro_repo_rechazada() -> None:
    repo = resolve_repo_root(BACKEND_ROOT)
    with pytest.raises(ValueError, match="dentro del repositorio"):
        assert_output_outside_repo(repo / "tmp_migracion_out", repo)


def test_cli_sin_db(tmp_path: Path) -> None:
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, [_row_base("cli-u", "2026-09-01")])
    out = tmp_path / "dry"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(csv_path),
            "--cutoff-date",
            "2026-10-01",
            "--output",
            str(out),
        ],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert (out / "resumen_actas_historicas.json").is_file()
    combined = proc.stdout + proc.stderr
    assert "Calle" not in combined
    assert "http" not in combined.lower()


def test_stdout_sin_pii(tmp_path: Path) -> None:
    csv_path = tmp_path / "pii.csv"
    row = _row_base("pii-u", "2026-09-01", dom="Secret Address 999")
    row[3] = "Juan Perez"
    _write_csv(csv_path, [row])
    out = tmp_path / "out2"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(csv_path),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
    )
    assert proc.returncode == 0
    assert "Secret" not in proc.stdout
    assert "Juan" not in proc.stdout


def test_allowed_columns_manifest_subset() -> None:
    hdr = _minimal_header()
    by = _header_indices(hdr)
    row = _row_base("x", "2026-09-01")
    snap = extract_row_snapshot(row, hdr, by)
    assert snap.ec5_uuid == "x"
    assert "ec5_uuid" in ALLOWED_LOGICAL_COLUMNS
