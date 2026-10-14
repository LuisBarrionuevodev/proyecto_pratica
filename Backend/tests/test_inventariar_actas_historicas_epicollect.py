"""Tests del inventario read-only EpiCollect (V1.1-MIG-ACTAS.0 / 0A)."""

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
from app.domains.migracion_historica.epicollect_cadenas_historicas import (
    EstadoVinculo as EV,
    ResultadoCadenaEsperado as RCE,
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
        "14_Nombre_de_Fantasa",
        "15_Razn_Socialnombre",
        "16_DNI_del_Contribuy",
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
    dom: str = "CALLE MITRE 100",
    inspeccion: str = "SI",
    num_ins: str = "1001",
    notif: str = "NO",
    num_not: str = "",
    comp: str = "NO",
    num_comp: str = "",
    ref_notif: str = "",
    dni: str = "20123456789",
    razon: str = "COMERCIO SA",
    nombre_fantasia: str = "",
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
        nombre_fantasia,
        razon,
        dni,
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
    row[13] = "SI"
    row[14] = "2002"
    row[15] = "SI"
    row[16] = "3003"
    _write_csv(csv_path, [row])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    assert result.filas[0].decision == Decision.CANDIDATA_CON_AMBAS_ACTAS


def test_clausura_decomiso_con_comprobacion(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    row = _row_base("u-cd", "2026-09-01", comp="SI", num_comp="4004")
    row[17] = "SI"
    row[18] = "5005"
    row[19] = "SI"
    row[20] = "6006"
    row[21] = "12"
    row[22] = "SI"
    row[23] = "SI"
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
    assert rein_snap.estado_vinculo == EV.VINCULO_CONFIABLE.value
    assert rein_snap.fuente_previa_uuid == "origen"


def test_reinspeccion_sin_referencia_o_duplicada_revisar(tmp_path: Path) -> None:
    csv_path = tmp_path / "t.csv"
    dup1 = _row_base("d1", "2026-08-01", notif="SI", num_not="7777", dni="11111111111")
    dup2 = _row_base("d2", "2026-08-02", notif="SI", num_not="7777", dni="22222222222")
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
    assert (out / "resumen_cadenas_historicas.json").is_file()
    combined = proc.stdout + proc.stderr
    assert "Calle" not in combined
    assert "http" not in combined.lower()


def test_stdout_sin_pii(tmp_path: Path) -> None:
    csv_path = tmp_path / "pii.csv"
    row = _row_base("pii-u", "2026-09-01", dom="Secret Address 999", razon="Juan Perez")
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


# --- V1.1-MIG-ACTAS.0A ---


def test_cadena_notif_dni_confiable_y_cerrada_sin_comprobacion(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad1.csv"
    origen = _row_base("o1", "2026-07-01", notif="SI", num_not="5001", dni="30999888777")
    rein = _row_base(
        "r1",
        "2026-08-01",
        tipo="Reinspección por Notificación",
        ref_notif="5001",
        dni="30999888777",
        comp="NO",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r1")
    assert r.estado_vinculo == EV.VINCULO_CONFIABLE.value
    assert r.resultado_cadena_esperado == RCE.CERRADA_SIN_COMPROBACION.value


def test_cadena_notif_con_comprobacion_en_reinspeccion(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad2.csv"
    origen = _row_base("o2", "2026-07-01", notif="SI", num_not="5002")
    rein = _row_base(
        "r2",
        "2026-08-01",
        tipo="Reinspección por Notificación",
        ref_notif="5002",
        comp="SI",
        num_comp="8008",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r2")
    assert r.resultado_cadena_esperado == RCE.CERRADA_CON_COMPROBACION.value


def test_cadena_comprobacion_oficio_expediente(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad3.csv"
    origen = _row_base("o3", "2026-06-01", comp="SI", num_comp="6001")
    origen[24] = "1000"
    origen[25] = "2026"
    origen[26] = "50"
    rein = _row_base(
        "r3",
        "2026-09-01",
        tipo="Verificar e Informar",
        dni="20123456789",
    )
    rein[24] = "1000"
    rein[25] = "2026"
    rein[26] = "50"
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r3")
    assert r.estado_vinculo == EV.VINCULO_CONFIABLE.value
    assert r.decision == Decision.CANDIDATA_REINSPECCION_OFICIO


def test_mismo_numero_acta_dni_distinto_conflictivo(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad4.csv"
    origen = _row_base("o4", "2026-07-01", notif="SI", num_not="9999", dni="11111111111")
    rein = _row_base(
        "r4",
        "2026-08-01",
        tipo="Reinspección por Notificación",
        ref_notif="9999",
        dni="22222222222",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r4")
    assert r.estado_vinculo == EV.VINCULO_CONFLICTIVO.value
    assert r.decision == Decision.REVISAR


def test_vinculo_por_domicilio_y_titular_sin_dni(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad5.csv"
    origen = _row_base(
        "o5",
        "2026-07-01",
        notif="SI",
        num_not="6006",
        dni="",
        dom="AV SAN MARTIN 200",
        razon="PANADERIA EL SOL",
    )
    rein = _row_base(
        "r5",
        "2026-08-15",
        tipo="Reinspección por Notificación",
        ref_notif="6006",
        dni="",
        dom="AV SAN MARTIN 200",
        razon="PANADERIA EL SOL",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r5")
    assert r.estado_vinculo == EV.VINCULO_CONFIABLE.value


def test_cronologia_reinspeccion_anterior_revisar(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad6.csv"
    origen = _row_base("o6", "2026-09-01", notif="SI", num_not="7007")
    rein = _row_base(
        "r6",
        "2026-08-01",
        tipo="Reinspección por Notificación",
        ref_notif="7007",
    )
    _write_csv(csv_path, [origen, rein])
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    r = next(s for s in result.filas if s.ec5_uuid == "r6")
    assert r.motivo_revision == "cronologia_invalida"
    assert r.decision == Decision.REVISAR


def test_salidas_cadenas_sin_pii(tmp_path: Path) -> None:
    csv_path = tmp_path / "cad7.csv"
    _write_csv(
        csv_path,
        [
            _row_base("o7", "2026-07-01", notif="SI", num_not="1", razon="EMPRESA X"),
            _row_base(
                "r7",
                "2026-08-01",
                tipo="Reinspección por Notificación",
                ref_notif="1",
                razon="EMPRESA X",
            ),
        ],
    )
    out = tmp_path / "outcad"
    result = inventariar_csv(csv_path, date(2026, 10, 1))
    write_inventario_outputs(result, out)
    blob = (out / "vinculos_confiables.csv").read_text(encoding="utf-8")
    assert "EMPRESA" not in blob
    assert "http" not in blob.lower()
    assert "9001" not in blob or "hash" in blob.lower()


# --- V1.1-MIG-ACTAS.0B ---


def _legacy_header_minimal() -> list[str]:
    return [
        "source_actuacion_id",
        "fecha_actuacion",
        "ot_anio",
        "tipo_actuacion",
        "numero_acta_notificacion",
        "numero_acta_comprobacion",
        "documento",
        "razon_social",
        "domicilio_texto",
        "numero_expediente",
        "anio_expediente",
        "numero_oficio",
        "estado_ruta_item",
    ]


def _write_legacy_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_legacy_header_minimal())
        for row in rows:
            w.writerow(row)


def _legacy_row(
    act_id: str,
    fecha: str,
    notif_num: str = "",
    comp_num: str = "",
    dni: str = "",
    razon: str = "",
    dom: str = "",
) -> list[str]:
    return [
        act_id,
        fecha,
        "2026",
        "INSPECCION",
        notif_num,
        comp_num,
        dni,
        razon,
        dom,
        "",
        "",
        "",
        "REALIZADO",
    ]


def test_legacy_resuelve_cuando_epi_sin_referencia(tmp_path: Path) -> None:
    epi = tmp_path / "epi.csv"
    legacy = tmp_path / "legacy.csv"
    rein = _row_base(
        "rein-l1",
        "2026-08-10",
        tipo="Reinspección por Notificación",
        ref_notif="88001",
        dni="27111222333",
        razon="KIOSCO SUR",
        dom="CALLE 9 50",
    )
    _write_csv(epi, [rein])
    _write_legacy_csv(
        legacy,
        [_legacy_row("99", "2026-07-01", notif_num="88001", dni="27111222333", razon="KIOSCO SUR", dom="CALLE 9 50")],
    )
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    r = next(s for s in result.filas if s.ec5_uuid == "rein-l1")
    assert r.estado_vinculo == EV.VINCULO_CONFIABLE.value
    assert r.origen_evidencia_vinculo == "MYSQL_HISTORICO"
    assert r.fuente_previa_legacy_hash


def test_legacy_ambos_fuentes_compatibles(tmp_path: Path) -> None:
    epi = tmp_path / "epi.csv"
    legacy = tmp_path / "legacy.csv"
    origen = _row_base("orig-b", "2026-07-01", notif="SI", num_not="88002", dni="20111222333")
    rein = _row_base(
        "rein-b",
        "2026-08-10",
        tipo="Reinspección por Notificación",
        ref_notif="88002",
        dni="20111222333",
    )
    _write_csv(epi, [origen, rein])
    _write_legacy_csv(legacy, [_legacy_row("100", "2026-07-01", notif_num="88002", dni="20111222333")])
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    r = next(s for s in result.filas if s.ec5_uuid == "rein-b")
    assert r.origen_evidencia_vinculo == "AMBOS"


def test_legacy_conflicto_fuentes(tmp_path: Path) -> None:
    epi = tmp_path / "epi.csv"
    legacy = tmp_path / "legacy.csv"
    origen = _row_base("orig-c", "2026-07-01", notif="SI", num_not="88003", dni="11111111111")
    rein = _row_base(
        "rein-c",
        "2026-08-10",
        tipo="Reinspección por Notificación",
        ref_notif="88003",
        dni="11111111111",
    )
    _write_csv(epi, [origen, rein])
    _write_legacy_csv(legacy, [_legacy_row("101", "2026-07-01", notif_num="88003", dni="22222222222")])
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    r = next(s for s in result.filas if s.ec5_uuid == "rein-c")
    assert r.estado_vinculo == EV.VINCULO_CONFLICTIVO.value
    assert r.motivo_revision == "conflicto_fuentes_epi_mysql"


def test_legacy_sin_identidad_parcial(tmp_path: Path) -> None:
    epi = tmp_path / "epi.csv"
    legacy = tmp_path / "legacy.csv"
    rein = _row_base(
        "rein-p",
        "2026-08-10",
        tipo="Reinspección por Notificación",
        ref_notif="88004",
    )
    _write_csv(epi, [rein])
    _write_legacy_csv(legacy, [_legacy_row("102", "2026-07-01", notif_num="88004")])
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    r = next(s for s in result.filas if s.ec5_uuid == "rein-p")
    assert r.estado_vinculo in (EV.VINCULO_PARCIAL.value, EV.SIN_REFERENCIA_PREVIA.value)


def test_compatibilidad_inventario_sin_columnas_identidad(tmp_path: Path) -> None:
    epi = tmp_path / "epi.csv"
    legacy = tmp_path / "legacy_min.csv"
    _write_csv(epi, [_row_base("x", "2026-09-01")])
    with legacy.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_actuacion_id", "fecha_actuacion", "tipo_actuacion"])
        w.writerow(["1", "2026-01-01", "INSPECCION"])
    out = tmp_path / "outleg"
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    write_inventario_outputs(result, out)
    compat = json.loads((out / "compatibilidad_inventario_mysql.json").read_text(encoding="utf-8"))
    assert compat["puede_elevar_vinculo_confiable"] is False


def test_legacy_salidas_sin_pii(tmp_path: Path) -> None:
    epi = tmp_path / "epi2.csv"
    legacy = tmp_path / "legacy2.csv"
    rein = _row_base(
        "rein-out",
        "2026-08-10",
        tipo="Reinspección por Notificación",
        ref_notif="88005",
        dni="30999888777",
        razon="SECRETO SA",
    )
    _write_csv(epi, [rein])
    _write_legacy_csv(
        legacy,
        [_legacy_row("103", "2026-07-01", notif_num="88005", dni="30999888777", razon="SECRETO SA")],
    )
    out = tmp_path / "outlegacy"
    result = inventariar_csv(epi, date(2026, 10, 1), legacy_inventory=legacy)
    write_inventario_outputs(result, out)
    blob = (out / "vinculos_resueltos_legacy.csv").read_text(encoding="utf-8")
    assert "SECRETO" not in blob
    assert "30999888777" not in blob
    assert "http" not in blob.lower()
