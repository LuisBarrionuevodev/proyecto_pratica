/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { CrudDialogActions } from "./CrudDialogActions";
import { CrudDialogHeader, crudDialogModeLabel } from "./CrudDialogHeader";
import { CrudDialogSection } from "./CrudDialogSection";
import { CrudFieldView, formatCrudFieldValue, CRUD_FIELD_EMPTY } from "./CrudFieldView";
import { CrudFormErrorSummary, scrollCrudDialogToTop } from "./CrudFormErrorSummary";
import { CrudFormSlot } from "./CrudFormSlot";
import { CrudGlassDialog } from "./CrudGlassDialog";
import { CRUD_FIELD_INPUT_HEIGHT_PX } from "../../styles/crudDialogTokens";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("CrudDialogHeader", () => {
  it("renderiza título, subtítulo y modo", () => {
    const html = render(
      <CrudDialogHeader
        domainChip="Relevamientos"
        titulo="Detalle"
        subtitulo="Calle Falsa 123"
        statusChip="Pendiente"
        mode="view"
      />
    );
    expect(html).toContain("Relevamientos");
    expect(html).toContain("Detalle");
    expect(html).toContain("Vista");
  });

  it("expone etiquetas de modo", () => {
    expect(crudDialogModeLabel("edit")).toBe("Edición");
    expect(crudDialogModeLabel("create")).toBe("Alta");
  });
});

describe("CrudDialogActions", () => {
  it("vista solo muestra Editar primary en fila horizontal", () => {
    const html = render(
      <CrudDialogActions
        mode="view"
        onEdit={() => undefined}
        extraActions={<button type="button">Imprimir</button>}
      />
    );
    expect(html).toContain("Editar");
    expect(html).toContain("Imprimir");
    expect(html).not.toContain("Cerrar");
    expect(html).not.toContain("Cancelar");
  });

  it("edición muestra Guardar y Eliminar opcional", () => {
    const html = render(
      <CrudDialogActions mode="edit" onSave={() => undefined} onDelete={() => undefined} showDelete />
    );
    expect(html).toContain("Guardar cambios");
    expect(html).toContain("Eliminar");
  });
});

describe("CrudFormSlot", () => {
  it("vista muestra label y valor en shell readonly tipo input", () => {
    const html = render(<CrudFormSlot label="Inspector" mode="view" value="García" />);
    expect(html).toContain("Inspector");
    expect(html).toContain("García");
    expect(html).toContain("rgba(255,255,255,0.12)");
    expect(html).toContain(`height:${CRUD_FIELD_INPUT_HEIGHT_PX}px`);
  });
});

describe("CrudFieldView", () => {
  it("usa fallback para valor vacío", () => {
    expect(formatCrudFieldValue(null)).toBe(CRUD_FIELD_EMPTY);
  });

  it("renderiza shell readonly vertical tipo input", () => {
    const html = render(<CrudFieldView label="Calle" value="San Martín" />);
    expect(html).toContain("Calle");
    expect(html).toContain("San Martín");
    expect(html).toContain("rgba(255,255,255,0.12)");
  });
});

describe("CrudFormErrorSummary", () => {
  it("scrollCrudDialogToTop desplaza el contenedor", () => {
    const el = { scrollTo: vi.fn() } as unknown as HTMLElement;
    scrollCrudDialogToTop(el, "auto");
    expect(el.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "auto" });
  });
});

describe("crudDialogTokens", () => {
  it("altura fija de campo es 40px", () => {
    expect(CRUD_FIELD_INPUT_HEIGHT_PX).toBe(40);
  });
});

describe("CrudGlassDialog scrollbar", () => {
  it("oculta scrollbar visual en contenido scrolleable", () => {
    const html = render(
      <CrudGlassDialog
        open
        disablePortal
        hideBackdrop
        onClose={() => undefined}
        onCloseButtonClick={() => undefined}
        title={<CrudDialogHeader titulo="Scroll" mode="view" />}
      >
        <p>Cuerpo largo</p>
      </CrudGlassDialog>
    );
    expect(html).toContain("scrollbar-width:none");
  });
});

describe("CrudGlassDialog", () => {
  it("renderiza sin Cancelar", () => {
    const html = render(
      <CrudGlassDialog
        open
        disablePortal
        hideBackdrop
        onClose={() => undefined}
        onCloseButtonClick={() => undefined}
        title={<CrudDialogHeader titulo="Prueba" mode="create" />}
        actions={<CrudDialogActions mode="create" onSave={() => undefined} saveLabel="Crear" />}
      >
        <p>Cuerpo</p>
      </CrudGlassDialog>
    );
    expect(html).toContain("Prueba");
    expect(html).not.toContain("Cancelar");
  });
});

describe("CrudDialogSection", () => {
  it("renderiza variante plain", () => {
    const html = render(
      <CrudDialogSection title="Domicilio">
        <span>Contenido</span>
      </CrudDialogSection>
    );
    expect(html).toContain("Domicilio");
  });
});
