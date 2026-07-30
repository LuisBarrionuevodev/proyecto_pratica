/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HistorialActasTramitesCell } from "./components/HistorialActasTramitesCell";
import { HistorialInspectoresCell } from "./components/HistorialInspectoresCell";
import { historialActasTramitesChipLabels } from "./utils/historialActasTramitesVisual";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("HistorialInspectoresCell", () => {
  it("muestra nombres separados por coma", () => {
    const html = render(
      <HistorialInspectoresCell inspectoresTexto="Zacarme Ariel, Villafañe Angel Antonio" />
    );
    expect(html).toContain("Zacarme Ariel");
    expect(html).toContain("Villafañe Angel Antonio");
  });

  it("sin inspectores muestra guión", () => {
    const html = render(<HistorialInspectoresCell inspectoresTexto={null} />);
    expect(html).toContain("—");
  });
});

describe("historialActasTramitesVisual", () => {
  it("arma chips en orden inspección → oficio", () => {
    const labels = historialActasTramitesChipLabels(
      {
        inspeccion: { texto: "086931/2026" },
        notificacion: { texto: "123/2026" },
        comprobacion: { texto: "456/2026" },
      },
      {
        expediente: { texto: "012388/2026" },
        oficio: { texto: "3489/2026" },
      }
    );
    expect(labels).toEqual([
      "Inspección 086931/2026",
      "Notificación 123/2026",
      "Comprobación 456/2026",
      "Expediente N.º 012388/2026",
      "Oficio N.º 3489/2026",
    ]);
  });

  it("sin actas ni trámites devuelve lista vacía", () => {
    expect(historialActasTramitesChipLabels(null, null)).toEqual([]);
  });
});

describe("HistorialActasTramitesCell", () => {
  it("renderiza chips cuando hay actas", () => {
    const html = render(
      <HistorialActasTramitesCell
        actas={{ inspeccion: { texto: "086931/2026" } }}
        tramites={{ expediente: { texto: "012388/2026" } }}
      />
    );
    expect(html).toContain("MuiChip-outlined");
    expect(html).toContain("Inspección 086931/2026");
    expect(html).toContain("Expediente N.º 012388/2026");
  });

  it("sin datos muestra guión", () => {
    const html = render(<HistorialActasTramitesCell actas={null} tramites={null} />);
    expect(html).toContain("—");
    expect(html).not.toContain("MuiChip-outlined");
  });
});
