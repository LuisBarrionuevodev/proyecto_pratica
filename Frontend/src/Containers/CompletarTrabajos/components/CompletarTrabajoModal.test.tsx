/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { CompletarTrabajoModal } from "./CompletarTrabajoModal";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("../../../api/completarTrabajoApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/completarTrabajoApi")>();
  return {
    ...mod,
    getCompletarTrabajoDetalle: vi.fn().mockRejectedValue(new Error("offline")),
  };
});

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function buildRow(
  overrides: Partial<ICompletarTrabajoPendienteRow> = {}
): ICompletarTrabajoPendienteRow {
  return {
    id: 9,
    ruta_item_id: 9,
    actuacion_id: 42,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 1,
    iniciador_ruta_id: 1,
    grupo_nombre: "Grupo Norte",
    tipo_iniciador: "RELEVAMIENTO",
    fecha_actuacion: "2026-05-10",
    orden_trabajo_numero: "123456",
    iniciador_estado: "EN_PROCESO",
    domicilio_texto: "San Martín 450",
    estado_operativo: "PENDIENTE",
    observaciones_ejecucion: null,
    calle: "San Martín",
    numero: "450",
    rubro_nombre: "Carnicería",
    doc_nro: "1234567",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    razon_social: null,
    nombre_local: null,
    tipo_actuacion: null,
    contraproducencia: null,
    inspectores: ["García", "López"],
    inspector1: "García",
    inspector2: "López",
    inspector3: null,
    ...overrides,
  };
}

const catalogs = {
  motivos: ["Falta de habilitación"],
  motivosComprobacion: ["Incumplimiento"],
  contraproducencias: ["No", "Sí"],
  inspectores: ["García", "López"],
  rubros: ["Carnicería"],
};

describe("CompletarTrabajoModal", () => {
  it("usa shell CRUD glass como Actuaciones", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow()}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Completar trabajo");
    expect(html).toContain("Guardar cierre");
    expect(html).not.toContain("Cancelar");
  });

  it("no muestra Alert error inline duplicado para validación", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow()}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).not.toContain("MuiAlert-standardError");
  });

  it("header muestra chip Completar trabajo sin chip Edición", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({ tipo_iniciador: "REINSPECCION_OFICIO", fecha_actuacion: "2026-06-28" })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Completar trabajo");
    expect(html).not.toContain("Edición");
    expect(html.match(/Completar trabajo/g)?.length).toBe(1);
  });

  it("header usa tipo de iniciador como título y fecha como subtítulo", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({ tipo_iniciador: "REINSPECCION_OFICIO", fecha_actuacion: "2026-06-28" })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Reinspección por oficio");
    expect(html).toContain("Fecha: 2026-06-28");
    expect(html).not.toContain("Cierre operativo");
    expect(html).not.toContain("Tipo de iniciador:");
  });

  it("ratificación promovida muestra título humanizado de ratificación", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({
          tipo_iniciador: "RATIFICACION_CLAUSURA_OFICIO",
          tipo_actuacion: "RATIFICACION DE CLAUSURA",
          fecha_actuacion: "2026-07-01",
        })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Ratificación de clausura");
    expect(html).not.toContain("Reinspección por oficio");
  });

  it("verificar e informar promovido muestra pregunta de nueva inspección", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({
          tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
          tipo_actuacion: "VERIFICAR E INFORMAR",
          fecha_actuacion: "2026-07-02",
        })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Verificar e informar");
    expect(html).toContain("¿Realizó nueva inspección?");
    expect(html).not.toContain("¿Dio cumplimiento?");
    expect(html).not.toContain("N° acta de inspección");
  });

  it("ratificación promovida no muestra nueva inspección", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({
          tipo_iniciador: "RATIFICACION_DECOMISO_OFICIO",
          tipo_actuacion: "RATIFICACION DE DECOMISO",
        })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("¿Dio cumplimiento?");
    expect(html).not.toContain("¿Realizó nueva inspección?");
  });

  it("reinspección por notificación muestra notificación origen readonly", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({
          tipo_iniciador: "REINSPECCION_NOTIFICACION",
          tipo_actuacion: "REINSPECCION",
          notificacion_origen_texto: "000123/2026",
        })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Notificación origen (solo lectura)");
    expect(html).toContain("Notif. 000123/2026");
    expect(html).not.toContain("N° acta de notificación");
  });

  it("reinspección por notificación sin origen muestra guión", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={buildRow({
          tipo_iniciador: "REINSPECCION_NOTIFICACION",
          tipo_actuacion: "REINSPECCION",
        })}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Notificación origen (solo lectura)");
    expect(html).toContain("—");
  });
});
