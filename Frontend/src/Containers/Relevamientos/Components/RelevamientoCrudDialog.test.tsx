/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { RelevamientoCrudDialog } from "./RelevamientoCrudDialog";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const baseRow: IRelevamientoListItem = {
  id: 7,
  fecha: "2026-05-10",
  inspector: "García",
  calle: "San Martín",
  calle_estado: "OK",
  calle_normalizada: "Av. San Martín",
  numero: "450",
  rubro: "Carnicería",
  turno: "MANIANA",
  esta_abierto: false,
  domicilio_id: 12,
  editable: true,
};

const catalogs = { inspectores: ["García", "López"], rubros: ["Carnicería"] };

describe("RelevamientoCrudDialog", () => {
  it("modo vista muestra Editar primary sin IDs en título", () => {
    const html = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="view"
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        onClose={() => undefined}
        onModeChange={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Relevamiento");
    expect(html).not.toContain("Relevamiento #");
    expect(html).not.toContain("Registro");
    expect(html).toContain("Editar");
    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("Guardar cambios");
  });

  it("modo edición muestra Guardar cambios y layout unificado", () => {
    const html = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="edit"
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        showDelete
        onClose={() => undefined}
        onDelete={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Editar relevamiento");
    expect(html).toContain("Guardar cambios");
    expect(html).toContain("Eliminar");
    expect(html).not.toContain("Cancelar");
  });

  it("muestra error global y error por campo", () => {
    const html = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="edit"
        draft={baseRow}
        fieldErrors={{ calle: "Calle inválida" }}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        globalError="No se pudo guardar"
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("No se pudo guardar");
    expect(html).toContain("Calle inválida");
  });
});
