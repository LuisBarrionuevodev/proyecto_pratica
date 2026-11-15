/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IVinculacionEstablecimientoPreview } from "../../../api/establecimientosOperativosApi";
import { VinculacionConfirmacionContent } from "./VinculacionConfirmacionContent";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function preview(
  partial: Partial<IVinculacionEstablecimientoPreview>
): IVinculacionEstablecimientoPreview {
  return {
    establecimiento_operativo_id: 1,
    puede_aplicar: true,
    situacion: "A",
    fingerprint: "a".repeat(64),
    conflicto: null,
    advertencias: [],
    establecimiento: {
      id: 1,
      domicilio_id: 9,
      domicilio_texto: "San Martín 100",
      domicilio_ids_ficha: [9],
      identidad_logica_completa: true,
    },
    contribuyente_actual: {
      id: 2,
      documento: "20111111111",
      apellido: "Erroneo",
      nombre: "Cuit",
      razon_social: null,
    },
    contribuyente_destino: {
      id: 3,
      documento: "20222222222",
      apellido: "Ocampo",
      nombre: "Carlos",
      razon_social: null,
    },
    alcance: {
      actuaciones: { cantidad: 4, ids: [] },
      notificaciones: { cantidad: 1, ids: [] },
      comprobaciones: { cantidad: 0, ids: [] },
      oficios: { cantidad: 0, ids: [] },
      iniciadores: { cantidad: 2, ids: [] },
      ruta_items: { cantidad: 1, ids: [] },
    },
    otros_locales_contribuyente_anterior: { cantidad: 0, ids: [] },
    otros_locales_contribuyente_destino: { cantidad: 1, ids: [] },
    ficha_logica_destino: { existe: false, establecimiento_operativo_id: null },
    edita_datos_destino: false,
    ...partial,
  };
}

describe("VinculacionConfirmacionContent", () => {
  it("muestra nombre, documento, alcance y no afirma el mismo local si es otro domicilio", () => {
    const html = render(<VinculacionConfirmacionContent preview={preview({})} />);
    expect(html).toContain("Carlos Ocampo");
    expect(html).toContain("CUIT/DNI: 20222222222");
    expect(html).toContain("¿Querés asociar este establecimiento a este contribuyente?");
    expect(html).toContain("Establecimiento:");
    expect(html).toContain("San Martín 100");
    expect(html).toContain("Historial:");
    expect(html).toContain("4 actuaciones");
    expect(html).toContain("Los demás establecimientos no se modificarán.");
    expect(html).toContain("Los documentos ya emitidos no se modifican.");
    expect(html).not.toContain("Las actuaciones de este domicilio se mostrarán juntas.");
    expect(html).not.toContain("iniciador");
    expect(html).not.toContain("ítems de ruta");
    expect(html).not.toContain("ficha #");
    expect(html).not.toContain("snapshot");
  });

  it("aclara antecedentes conjuntos solo si ya existe ficha lógica del mismo domicilio", () => {
    const html = render(
      <VinculacionConfirmacionContent
        preview={preview({
          situacion: "B",
          ficha_logica_destino: { existe: true, establecimiento_operativo_id: 88 },
        })}
      />
    );
    expect(html).toContain("Las actuaciones de este domicilio se mostrarán juntas.");
    expect(html).not.toContain("ficha #88");
  });

  it("conflicto inseguro: un solo mensaje y no ofrece asociar con datos inventados", () => {
    const html = render(
      <VinculacionConfirmacionContent
        preview={preview({
          puede_aplicar: false,
          situacion: "BLOQUEO",
          fingerprint: null,
          contribuyente_destino: null,
          conflicto: {
            codigo: "DOCUMENTO_AMBIGUO",
            detail: "Hay más de un contribuyente activo con ese documento.",
          },
        })}
      />
    );
    expect(html).toContain("No pudimos identificar el vínculo con seguridad.");
    expect(html).toContain("Hay más de un contribuyente activo con ese documento.");
    expect(html).not.toContain("¿Querés asociar este establecimiento a este contribuyente?");
    expect(html).not.toContain("Carlos Ocampo");
  });
});
