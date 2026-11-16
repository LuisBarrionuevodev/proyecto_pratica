/** @jsxImportSource react */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IVinculacionEstablecimientoPreview } from "../../../api/establecimientosOperativosApi";
import { VinculacionConfirmacionContent } from "./VinculacionConfirmacionContent";

const theme = createTheme();
const srcPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "VinculacionConfirmacionContent.tsx");

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
  it("destaca contribuyente, domicilio y historial compacto sin afirmar el mismo local", () => {
    const html = render(<VinculacionConfirmacionContent preview={preview({})} />);
    expect(html).toContain("Contribuyente encontrado");
    expect(html).toContain("Carlos Ocampo");
    expect(html).toContain("CUIT/DNI: 20222222222");
    expect(html).toContain("¿Querés asociar este establecimiento a Carlos Ocampo?");
    expect(html).toContain("Establecimiento");
    expect(html).toContain("San Martín 100");
    expect(html).toContain("Historial que se asociará");
    expect(html).toContain("4 actuaciones");
    expect(html).toContain("1 notificación");
    expect(html).toContain("0 comprobaciones");
    expect(html).toContain("Los demás establecimientos no se modificarán.");
    expect(html).toContain("Los datos personales del contribuyente encontrado se conservan.");
    expect(html).toContain("Los documentos ya emitidos conservarán sus datos.");
    expect(html).not.toContain("Las actuaciones de este domicilio se mostrarán juntas.");
    expect(html).not.toContain("iniciador");
    expect(html).not.toContain("ítems de ruta");
    expect(html).not.toContain("ficha #");
    expect(html).not.toContain("snapshot");
  });

  it("usa pregunta genérica si falta el nombre y no lo inventa", () => {
    const html = render(
      <VinculacionConfirmacionContent
        preview={preview({
          contribuyente_destino: {
            id: 3,
            documento: "20222222222",
            apellido: null,
            nombre: null,
            razon_social: null,
          },
        })}
      />
    );
    expect(html).toContain("¿Querés asociar este establecimiento a este contribuyente?");
    expect(html).not.toContain("¿Querés asociar este establecimiento a —");
    expect(html).toContain("CUIT/DNI: 20222222222");
  });

  it("detalle arranca cerrado, con ceros disponibles y control accesible", () => {
    const html = render(<VinculacionConfirmacionContent preview={preview({})} />);
    expect(html).toContain("Ver detalle del alcance");
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain("aria-controls");
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("MuiCollapse-hidden");
    expect(html).not.toContain("Ocultar detalle del alcance");
    expect(html).toContain("Oficios");
    expect(html).toContain(">0<");
    expect(html).toContain("grid-template-columns");
  });

  it("en alta muestra propuesto, actual y aclara que no es cambio de dueño", () => {
    const html = render(
      <VinculacionConfirmacionContent
        preview={preview({
          situacion: "ALTA",
          crea_contribuyente: true,
          contribuyente_destino: {
            id: null,
            documento: "20333333333",
            apellido: "Nuevo",
            nombre: "Titular",
            razon_social: null,
          },
        })}
      />
    );
    expect(html).toContain("Contribuyente propuesto");
    expect(html).toContain("Titular Nuevo");
    expect(html).toContain("Contribuyente actual");
    expect(html).toContain("titular cargado por error");
    expect(html).not.toContain("Los datos personales del contribuyente encontrado se conservan.");
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
    expect(html).toContain("MuiAlert-standardWarning");
    expect(html).not.toContain("MuiAlert-standardInfo");
    expect(html).not.toContain("¿Querés asociar este establecimiento a este contribuyente?");
    expect(html).not.toContain("Carlos Ocampo");
  });

  it("envuelve nombres y domicilios largos", () => {
    const largo =
      "Cooperativa de Provisión de Servicios Comunitarios y Desarrollo Productivo del Norte Argentino Limitada";
    const domicilioLargo =
      "Avenida de los Inmigrantes de la República Argentina 1234 esquina Boulevard del Libertador General San Martín";
    const html = render(
      <VinculacionConfirmacionContent
        preview={preview({
          contribuyente_destino: {
            id: 3,
            documento: "20333333333",
            apellido: null,
            nombre: null,
            razon_social: largo,
          },
          establecimiento: {
            id: 1,
            domicilio_id: 9,
            domicilio_texto: domicilioLargo,
            domicilio_ids_ficha: [9],
            identidad_logica_completa: true,
          },
        })}
      />
    );
    expect(html).toContain(largo);
    expect(html).toContain(domicilioLargo);
    expect(html).toContain("break-word");
    expect(html).toContain(`¿Querés asociar este establecimiento a ${largo}?`);
  });

  it("el control de detalle se abre y cierra por botón nativo con estado aria", () => {
    const src = readFileSync(srcPath, "utf8");
    expect(src).toContain("aria-expanded={detalleOpen}");
    expect(src).toContain("aria-controls={detalleId}");
    expect(src).toContain('type="button"');
    expect(src).toContain("setDetalleOpen((open) => !open)");
    expect(src).toContain("VINCULACION_OCULTAR_DETALLE");
    expect(src).toContain("ExpandMoreIcon");
    expect(src).toContain('useState(false)');
    expect(src).not.toContain("aplicarVinculacionEstablecimiento");
    expect(src).not.toContain("fingerprint");
  });
});
