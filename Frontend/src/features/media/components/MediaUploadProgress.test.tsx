import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MediaUploadProgress } from "./MediaUploadProgress";

vi.mock("../../../theme/DigitalizaThemeProvider", () => ({
  useDigitalizaTheme: () => ({
    mode: "light" as const,
    colors: {
      text: { primary: "#18202C", muted: "#5C6773" },
      border: { default: "#D8DEE6" },
    },
  }),
}));
import type { MediaQueuedFile } from "../mediaTypes";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";

function item(phase: MediaQueuedFile["phase"], idx = 1): MediaQueuedFile {
  return {
    localId: `mq-${idx}`,
    file: new File(["x"], `foto-${idx}.jpg`, { type: "image/jpeg" }),
    categoria: MEDIA_CATEGORIA_FOTO_ACTA,
    tipoDocumento: null,
    phase,
    progressPct: phase === "uploading" ? 40 : 0,
    errorMessage: null,
    archivoId: null,
    previewUrl: null,
  };
}

describe("MediaUploadProgress", () => {
  it("muestra contador N/Total y aviso durante carga", () => {
    const html = renderToStaticMarkup(
      <MediaUploadProgress
        open
        sessionActive
        globalPct={30}
        items={[item("ready", 1), item("uploading", 2), item("pending", 3)]}
      />
    );
    expect(html).toContain("Subiendo fotos");
    expect(html).toContain("No cierres esta pantalla");
    expect(html).toMatch(/2\s*\/\s*3/);
  });

  it("muestra estado final de éxito", () => {
    const html = renderToStaticMarkup(
      <MediaUploadProgress
        open
        sessionActive={false}
        globalPct={100}
        items={[item("ready", 1), item("ready", 2)]}
      />
    );
    expect(html).toContain("Fotos cargadas correctamente");
    expect(html).toContain("Carga finalizada");
  });

  it("muestra copy de carga interrumpida", () => {
    const html = renderToStaticMarkup(
      <MediaUploadProgress
        open
        sessionActive={false}
        globalPct={50}
        items={[item("ready", 1), item("error", 2)]}
      />
    );
    expect(html).toContain("Carga interrumpida");
    expect(html).toContain("Se guardaron las fotos anteriores");
  });
});
