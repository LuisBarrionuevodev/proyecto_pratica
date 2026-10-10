/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ActuacionMediaGallery } from "./components/ActuacionMediaGallery";
import { MEDIA_RUTA_ITEM_GALLERIES } from "./mediaConstants";

const theme = createTheme();

vi.mock("../../api/mediaApi", () => ({
  getRutaItemArchivos: vi.fn().mockResolvedValue({
    foto_acta: [],
    foto_documentacion_local: [],
    foto_inspeccion: [],
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

vi.mock("./components/MediaUploadProgress", () => ({
  MediaUploadProgress: () => null,
}));

vi.mock("./mediaUploadPipeline", () => ({
  uploadQueuedFilesWithConcurrency: vi.fn(async () => undefined),
}));

describe("ActuacionMediaGallery MEDIA.1B", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza exactamente tres galerías sin duplicados", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly={false} hideTitle />
      </ThemeProvider>
    );
    expect(MEDIA_RUTA_ITEM_GALLERIES).toHaveLength(3);
    const docCount = (html.match(/Fotos de la documentación del local/g) ?? []).length;
    const actaCount = (html.match(/Fotos de las actas/g) ?? []).length;
    const inspCount = (html.match(/Fotos de la inspección/g) ?? []).length;
    expect(docCount).toBe(1);
    expect(actaCount).toBe(1);
    expect(inspCount).toBe(1);
    expect(html).not.toContain("Tipo de documento");
  });

  it("en edición muestra tres botones Seleccionar archivos", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly={false} hideTitle />
      </ThemeProvider>
    );
    expect((html.match(/Seleccionar archivos/g) ?? []).length).toBe(3);
  });

  it("modo manualSave muestra Pendiente de guardar", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionMediaGallery rutaItemId={42} readOnly={false} hideTitle manualSave />
      </ThemeProvider>
    );
    expect(html).toContain("CONTINUAR SUBIDA");
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
