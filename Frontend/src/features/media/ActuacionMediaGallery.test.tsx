/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ActuacionMediaGallery } from "./components/ActuacionMediaGallery";
import { MEDIA_1A_GALLERIES } from "./mediaConstants";

const theme = createTheme();

vi.mock("../../api/mediaApi", () => ({
  getRutaItemArchivos: vi.fn().mockResolvedValue({
    foto_acta: [],
    foto_documentacion_local: [],
  }),
  getMediaDownloadUrl: vi.fn(),
  deleteArchivo: vi.fn(),
  postMediaUploadIntent: vi.fn(),
  postMediaComplete: vi.fn(),
}));

vi.mock("../../components/feedback", () => ({
  useAppFeedback: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  }),
}));

describe("ActuacionMediaGallery MEDIA.1A.4", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza exactamente dos galerías Media.1A", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly={false} hideTitle />
      </ThemeProvider>
    );
    expect(MEDIA_1A_GALLERIES).toHaveLength(2);
    const docCount = (html.match(/Fotos de la documentación del local/g) ?? []).length;
    const actaCount = (html.match(/Fotos de las actas/g) ?? []).length;
    expect(docCount).toBe(1);
    expect(actaCount).toBe(1);
    expect(html).not.toMatch(/inspección/i);
    expect(html).not.toContain("FOTO_INSPECCION");
  });

  it("en edición muestra dos botones Seleccionar archivos", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly={false} hideTitle />
      </ThemeProvider>
    );
    expect((html.match(/Seleccionar archivos/g) ?? []).length).toBe(2);
  });

  it("en solo lectura no muestra Seleccionar archivos", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly hideTitle />
      </ThemeProvider>
    );
    expect(html).not.toContain("Seleccionar archivos");
  });
});
