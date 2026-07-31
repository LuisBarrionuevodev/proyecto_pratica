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
  });

  it("loading usa overlay spinner, no progress bars MRT", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain('loadingMode="overlay"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain("showProgressBars");
  });

  it("RubroChip reutiliza bandejaOutlinedChipSx", () => {
    const src = readFileSync(rubroChipPath, "utf8");
    expect(src).toContain("bandejaOutlinedChipSx");
    const html = renderToStaticMarkup(<RubroChip rubro="Panadería" />);
    expect(html).toContain("MuiChip-outlined");
  });
});

describe("UI consistencia PR — loading spinner", () => {
  it("Relevamientos gestión usa overlay sin showProgressBars", () => {
    const src = readFileSync(relevamientosTablePath, "utf8");
    expect(src).toContain('loadingMode="overlay"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain("showProgressBars");
  });

  it("Denuncias usa BandejaTableSpinner, no texto de carga", () => {
    const src = readFileSync(denunciasTablePath, "utf8");
    expect(src).toContain("BandejaTableSpinner");
    expect(src).not.toContain("Cargando denuncias");
    expect(src).not.toContain("loadingStyles");
  });

  it("Perfiles (gestión usuarios) usa overlay sin showProgressBars", () => {
    const src = readFileSync(perfilesTablePath, "utf8");
    expect(src).toContain('loadingMode="overlay"');
    expect(src).toContain("BANDEJA_MRT_SPINNER_LOADING_STATE");
    expect(src).not.toContain("showProgressBars");
  });

  it("Perfil usuario usa CircularProgress sin Slide", () => {
    const src = readFileSync(perfilPagePath, "utf8");
    expect(src).toContain("CircularProgress");
    expect(src).not.toContain("Slide");
    expect(src).not.toContain("Skeleton");
  });
});
