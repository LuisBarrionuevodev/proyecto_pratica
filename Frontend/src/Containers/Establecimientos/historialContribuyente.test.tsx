/** @jsxImportSource react */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { buildHistorialContribuyenteColumns } from "./historialContribuyenteColumns";
import { historialContribuyenteDomicilioTexto } from "./utils/historialContribuyenteDomicilio";
import {
  documentoHistorialInputValid,
  MSG_DOCUMENTO_HISTORIAL_VACIO,
} from "./utils/historialContribuyenteDocumento";
import { HistorialActasTramitesCell } from "./components/HistorialActasTramitesCell";
import { HistorialInspectoresCell } from "./components/HistorialInspectoresCell";
import { RubroChip } from "./components/RubroChip";
import {
  BandejaTipoActuacionChipCell,
  contraproducenciaBandejaSegment,
} from "../Actuaciones/Components/bandejaTableCells";
import type { IHistorialContribuyenteRow } from "../../api/historialContribuyenteApi";

const baseDir = fileURLToPath(new URL(".", import.meta.url));
const pagePath = resolve(baseDir, "HistorialContribuyentePage.tsx");
const apiPath = resolve(baseDir, "../../api/historialContribuyenteApi.ts");
const hookPath = resolve(baseDir, "hooks/useHistorialContribuyente.ts");

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const sampleRow: IHistorialContribuyenteRow = {
  id: 1,
  fecha: "2026-03-15",
  tipo_actuacion: "INSPECCION",
  contraproducencia: "LOCAL CERRADO",
  domicilio_texto: "San Martín 100",
  rubro_nombre: "Panadería",
  inspectores_texto: "Inspector Uno",
  estado: "REALIZADA",
  actas: { inspeccion: { texto: "086931/2026" }, notificacion: { texto: "123/2026" } },
  tramites: { expediente: { texto: "012388/2026" }, oficio: { texto: "3489/2026" } },
};

describe("historialContribuyenteDocumento", () => {
  it("acepta documentos con separadores", () => {
    expect(documentoHistorialInputValid("42006775")).toBe(true);
    expect(documentoHistorialInputValid("42.006.775")).toBe(true);
    expect(documentoHistorialInputValid("20-33344455-5")).toBe(true);
    expect(documentoHistorialInputValid("  20333444555  ")).toBe(true);
  });

  it("rechaza vacío o sin dígitos", () => {
    expect(documentoHistorialInputValid("")).toBe(false);
    expect(documentoHistorialInputValid("   ")).toBe(false);
    expect(documentoHistorialInputValid("abc")).toBe(false);
    expect(MSG_DOCUMENTO_HISTORIAL_VACIO).toContain("DNI/CUIT");
  });
});

describe("historialContribuyenteDomicilio", () => {
  it("prioriza domicilio_texto del API", () => {
    expect(historialContribuyenteDomicilioTexto({ domicilio_texto: "Catamarca 500" })).toBe(
      "Catamarca 500"
    );
    expect(historialContribuyenteDomicilioTexto({ domicilio_texto: null })).toBe("—");
  });
});

describe("buildHistorialContribuyenteColumns", () => {
  it("incluye columnas requeridas en orden", () => {
    const cols = buildHistorialContribuyenteColumns();
    const headers = cols.map((c) => c.header);
    expect(headers).toEqual([
      "FECHA",
      "TIPO DE ACTUACIÓN",
      "DOMICILIO",
      "RUBRO",
      "INSPECTORES",
      "ACTAS Y TRÁMITES",
      "ESTADO",
    ]);
  });

  it("tipo de actuación usa chip compartido con contraproducencia", () => {
    const tipoCol = buildHistorialContribuyenteColumns().find((c) => c.header === "TIPO DE ACTUACIÓN");
    expect(tipoCol?.Cell).toBeDefined();
    const html = render(
      <BandejaTipoActuacionChipCell tipo="INSPECCION" contraproducencia="LOCAL CERRADO" />
    );
    expect(html).toContain("MuiChip-outlined");
    expect(contraproducenciaBandejaSegment("LOCAL CERRADO")).toContain("Contraproducencia");
  });

  it("domicilio usa domicilio_texto", () => {
    expect(historialContribuyenteDomicilioTexto(sampleRow)).toBe("San Martín 100");
  });

  it("rubro usa chip estilo bandeja", () => {
    const html = render(<RubroChip rubro="Panadería" />);
    expect(html).toContain("MuiChip-outlined");
    expect(html).toContain("Panadería");
  });

  it("inspectores y actas reutilizan celdas del historial por ficha", () => {
    const htmlInsp = render(<HistorialInspectoresCell inspectoresTexto="Inspector Uno" />);
    expect(htmlInsp).toContain("Inspector Uno");
    const htmlActas = render(
      <HistorialActasTramitesCell actas={sampleRow.actas ?? null} tramites={sampleRow.tramites ?? null} />
    );
    expect(htmlActas).toContain("Inspección 086931/2026");
    expect(htmlActas).toContain("Oficio N.º 3489/2026");
  });
});

describe("HistorialContribuyentePage estructura PR10.4c", () => {
  it("render inicial: input, sin tabla MRT overlay ni mensaje guía inicial", () => {
    const src = readFileSync(pagePath, "utf8");
    expect(src).toContain('label="DNI/CUIT"');
    expect(src).not.toContain("MSG_DOCUMENTO_HISTORIAL_VACIO");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).not.toContain('loadingMode="overlay"');
    expect(src).not.toContain("showProgressBars");
    expect(src).toContain("hasSearched && (loading || rows.length > 0)");
  });

  it("hook valida documento vacío antes de llamar API", () => {
    const hookSrc = readFileSync(hookPath, "utf8");
    expect(hookSrc).toContain("documentoHistorialInputValid");
    expect(hookSrc).toContain("MSG_DOCUMENTO_HISTORIAL_VACIO");
    expect(hookSrc).toContain("getHistorialContribuyente");
  });

  it("API apunta al endpoint de solo consulta", () => {
    const apiSrc = readFileSync(apiPath, "utf8");
    expect(apiSrc).toContain("/establecimientos/historial-contribuyente");
    expect(apiSrc).toContain("rows");
    expect(apiSrc).not.toMatch(/\/prefill|getPrefill|prefillContribuyente/i);
    expect(apiSrc).not.toMatch(/completar-trabajo|completarTrabajo/i);
  });

  it("mensaje de vacío tras búsqueda sin resultados", () => {
    const src = readFileSync(pagePath, "utf8");
    expect(src).toContain("No se encontraron actuaciones para este DNI/CUIT");
  });

  it("resumen bandeja con total y página tras búsqueda", () => {
    const src = readFileSync(pagePath, "utf8");
    expect(src).toContain("BandejaTableSummary");
    expect(src).toContain('label="Total"');
    expect(src).toContain('label="Página"');
    expect(src).toContain('label="DNI/CUIT"');
  });
});

describe("getHistorialContribuyente API client", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("arma params documento y paginación", async () => {
    const getMock = vi.fn().mockResolvedValue({
      data: {
        rows: [],
        meta: { total: 0, page: 1, limit: 20, documento_normalizado: "42006775" },
      },
    });
    vi.doMock("../../api/apiClient", () => ({
      apiClient: { get: getMock },
    }));

    const { getHistorialContribuyente } = await import("../../api/historialContribuyenteApi");
    await getHistorialContribuyente({ documento: "42.006.775", page: 2, limit: 20 });

    expect(getMock).toHaveBeenCalledWith("/establecimientos/historial-contribuyente", {
      params: { documento: "42.006.775", page: "2", limit: "20" },
    });
  });
});
