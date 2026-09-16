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
  relevadores_label: "García",
  relevador_ids: [1],
  relevadores: [{ id: 1, nombre: "García" }],
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

const catalogs = {
  relevadores: [
    { id: 1, nombre: "García" },
    { id: 2, nombre: "López" },
  ],
  rubros: ["Carnicería"],
};

import { buildNumeroTipoDraftPatch, relevamientoRowParaEdicion } from "../utils/relevamientoCamposForm";

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

  it("modo edición muestra Nombre fantasía siempre", () => {
    const html = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="edit"
        draft={{ ...baseRow, nombre_fantasia: "El Toro" }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Nombre fantasía");
    expect(html).toContain("Opcional. Sirve para distinguir locales en una misma esquina.");
  });

  it("REL-ANGULO.2: muestra Orientación solo en ESQUINA y labels por modo", () => {
    const esquinaHtml = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="edit"
        draft={{
          ...baseRow,
          numero_tipo: "ESQUINA",
          numero: "Belgrano y Mitre",
          angulo_esquina: "NE",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(esquinaHtml).toContain("Calle de esquina");
    expect(esquinaHtml).toContain("Orientación");
    expect(esquinaHtml).toContain("Ubicación del local en la esquina: NE, NO, SE o SO.");

    const numeroHtml = render(
      <RelevamientoCrudDialog
        open
        disablePortal
        mode="edit"
        draft={{ ...baseRow, numero_tipo: "NUMERO", numero: "450" }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        numeroEditorLabel="Número"
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(numeroHtml).not.toContain("Calle de esquina");
    expect(numeroHtml).not.toContain("Orientación");
  });

  it("cambiar ESQUINA → NUMERO limpia ángulo y número en patch", () => {
    expect(buildNumeroTipoDraftPatch("NUMERO")).toEqual({
      numero_tipo: "NUMERO",
      angulo_esquina: null,
    });
    expect(
      buildNumeroTipoDraftPatch("NUMERO", { numero_tipo: "ESQUINA", numero: "Belgrano y Mitre" })
    ).toEqual({
      numero_tipo: "NUMERO",
      angulo_esquina: null,
      numero: "",
    });
  });

  it("hidrata calle normalizada para edición", () => {
    const hydrated = relevamientoRowParaEdicion(baseRow);
    expect(hydrated.calle).toBe("Av. San Martín");
    expect(hydrated.numero).toBe("450");
  });
});
