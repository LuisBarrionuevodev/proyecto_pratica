/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

import { InspectorFotosPendientesBanner } from "./InspectorFotosPendientesBanner";

vi.mock("../hooks/useInspectorFotosPendientesCount", () => ({
  useInspectorFotosPendientesCount: vi.fn(),
}));

import { useInspectorFotosPendientesCount } from "../hooks/useInspectorFotosPendientesCount";

const theme = createTheme();

function renderBanner() {
  return renderToStaticMarkup(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <InspectorFotosPendientesBanner />
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe("InspectorFotosPendientesBanner", () => {
  it("oculta el aviso sin pendientes", () => {
    vi.mocked(useInspectorFotosPendientesCount).mockReturnValue({ count: 0, enabled: true });
    expect(renderBanner()).toBe("");
  });

  it("muestra aviso singular y enlace a Completar trabajos", () => {
    vi.mocked(useInspectorFotosPendientesCount).mockReturnValue({ count: 1, enabled: true });
    const html = renderBanner();
    expect(html).toContain("Te faltan subir fotos por una falla de conexión.");
    expect(html).toContain("Ir a Completar trabajos");
    expect(html).toContain("/completarTrabajos");
  });

  it("muestra cantidad cuando hay varios trabajos", () => {
    vi.mocked(useInspectorFotosPendientesCount).mockReturnValue({ count: 2, enabled: true });
    expect(renderBanner()).toContain("Te faltan subir fotos en 2 trabajos.");
  });
});
