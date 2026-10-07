import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MediaUploadPanelErrorBoundary } from "./MediaUploadPanelErrorBoundary";

describe("MediaUploadPanelErrorBoundary", () => {
  it("renderiza hijos cuando no hay error", () => {
    const html = renderToStaticMarkup(
      <MediaUploadPanelErrorBoundary resetKey={1} rutaItemId={5} onClosePanel={vi.fn()}>
        <span data-panel="ok">Panel fotos</span>
      </MediaUploadPanelErrorBoundary>
    );
    expect(html).toMatch(/Panel fotos/);
  });

  it("getDerivedStateFromError permite UI recuperable", () => {
    const state = MediaUploadPanelErrorBoundary.getDerivedStateFromError(new Error("boom"));
    expect(state.hasError).toBe(true);
    expect(state.message).toBe("boom");
  });
});
