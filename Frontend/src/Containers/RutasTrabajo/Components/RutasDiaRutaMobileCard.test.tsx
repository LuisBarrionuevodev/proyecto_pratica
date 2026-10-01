/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { RutasDiaRutaMobileCard } from "./RutasDiaRutaMobileCard";

const theme = createTheme();

const sample: IRutaTrabajo = {
  id: 9,
  fecha: "2026-03-15",
  turno: "MANIANA",
  estado_ruta: "BORRADOR",
  numero: 7,
  observaciones: null,
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

describe("RutasDiaRutaMobileCard", () => {
  it("muestra número, turno y affordance de apertura", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <RutasDiaRutaMobileCard ruta={sample} tab="borradores" onOpen={vi.fn()} />
      </ThemeProvider>
    );
    expect(html).toContain("Ruta 7");
    expect(html).toContain("Mañana");
    expect(html).toContain("Borrador");
    expect(html).toContain("Abrir ruta");
    expect(html).toContain('aria-label="Abrir ruta"');
    expect(html.match(/<button\b/g)?.length ?? 0).toBe(1);
    expect(html).not.toContain("MuiIconButton-root");
  });
});
