import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RubroChip } from "./components/RubroChip";

const listPagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "EstablecimientosListPage.tsx"
);
const historialPagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "HistorialContribuyentePage.tsx"
);
const rubroChipPath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "components/RubroChip.tsx"
);
const relevamientosTablePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../Relevamientos/Components/TableRelevamientos.tsx"
);
const denunciasTablePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../Relevamientos/Components/TableDenuncias.tsx"
);
const perfilesTablePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../GestionDeUsuarios/Components/TableGestionDeUsuarios.tsx"
);
const perfilPagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../Perfil/index.tsx"
);

describe("UI consistencia PR — Establecimientos", () => {
  it("botón Ver ficha usa variant primary", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain('dsVariant="primary"');
    expect(src).toContain("Ver ficha");
    expect(src).not.toContain('dsVariant="secondary"');
    expect(src).not.toContain("exportButtonStyles");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("Exportar");
  });

  it("loading usa BandejaTableSpinner sin overlay MRT", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).toContain('loadingMode="none"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain('loadingMode="overlay"');
    expect(src).not.toContain("showProgressBars");
  });

  it("RubroChip reutiliza bandejaOutlinedChipSx", () => {
    const src = readFileSync(rubroChipPath, "utf8");
    expect(src).toContain("bandejaOutlinedChipSx");
    const html = renderToStaticMarkup(<RubroChip rubro="Panadería" />);
    expect(html).toContain("MuiChip-outlined");
  });

  it("fichas operativas muestra resumen Total / Mostrando / Página", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain("BandejaTableSummary");
    expect(src).toContain('label="Total"');
    expect(src).toContain('label="Mostrando"');
    expect(src).toContain('label="Página"');
    expect(src).not.toContain("Completá criterios de búsqueda");
  });

  it("historial DNI/CUIT usa resumen bandeja y sin textos explicativos largos", () => {
    const src = readFileSync(historialPagePath, "utf8");
    expect(src).toContain("BandejaTableSummary");
    expect(src).toContain('label="Total"');
    expect(src).toContain('label="Página"');
    expect(src).not.toContain("Consultá el historial completo");
    expect(src).not.toContain("MSG_DOCUMENTO_HISTORIAL_VACIO");
    expect(src).not.toContain("Total de registros");
    expect(src).not.toContain("DNI/CUIT consultado:");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("Exportar");
  });
});

describe("UI consistencia PR — loading spinner", () => {
  it("Relevamientos gestión usa BandejaTableSpinner sin overlay MRT", () => {
    const src = readFileSync(relevamientosTablePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).toContain('loadingMode="none"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain('loadingMode="overlay"');
    expect(src).not.toContain("showProgressBars");
    expect(src).not.toContain("TablaExportButtons");
  });

  it("Denuncias usa BandejaTableSpinner, no texto de carga ni export", () => {
    const src = readFileSync(denunciasTablePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).not.toContain("Cargando denuncias");
    expect(src).not.toContain("loadingStyles");
    expect(src).not.toContain("TablaExportButtons");
  });

  it("Perfiles (gestión usuarios) usa BandejaTableSpinner sin overlay MRT", () => {
    const src = readFileSync(perfilesTablePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).toContain('loadingMode="none"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain('loadingMode="overlay"');
    expect(src).not.toContain("showProgressBars");
  });

  it("Perfil usuario usa BandejaTableSpinner sin Slide", () => {
    const src = readFileSync(perfilPagePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).not.toContain("Slide");
    expect(src).not.toContain("Skeleton");
  });
});
