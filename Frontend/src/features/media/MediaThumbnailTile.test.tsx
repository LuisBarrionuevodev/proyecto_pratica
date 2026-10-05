/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MediaThumbnailTile } from "./components/MediaThumbnailTile";
import type { MediaArchivoListItem } from "./mediaTypes";

const theme = createTheme();

vi.mock("../../api/mediaApi", () => ({
  getMediaDownloadUrl: vi.fn().mockResolvedValue({ download_url: "https://example.com/x.jpg" }),
}));

const imageItem: MediaArchivoListItem = {
  archivo_id: 1,
  original_filename: "foto_local.jpg",
  content_type: "image/jpeg",
  byte_size: 204800,
  categoria: "foto_inspeccion",
};

const pdfItem: MediaArchivoListItem = {
  archivo_id: 2,
  original_filename: "acta.pdf",
  content_type: "application/pdf",
  byte_size: 512000,
  categoria: "foto_acta",
};

describe("MediaThumbnailTile RESP-ACT.1", () => {
  it("imagen no muestra barra con nombre ni KB", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <MediaThumbnailTile item={imageItem} onOpen={() => undefined} />
      </ThemeProvider>
    );
    expect(html).toContain('aria-label="Ver imagen: foto_local.jpg"');
    expect(html).not.toMatch(/MuiImageListItemBar/);
    expect(html).not.toContain("200 KB");
  });

  it("PDF conserva identificación mínima", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <MediaThumbnailTile item={pdfItem} onOpen={() => undefined} />
      </ThemeProvider>
    );
    expect(html).toContain("acta.pdf");
    expect(html).toContain("PDF");
  });
});
