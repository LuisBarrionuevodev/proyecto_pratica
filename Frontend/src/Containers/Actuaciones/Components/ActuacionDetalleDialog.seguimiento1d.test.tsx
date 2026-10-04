/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { ActuacionDetalleDialog } from "./ActuacionDetalleDialog";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("../../../api/geolocalizacionApi", () => ({
  fetchCallesCatalogo: vi.fn(),
}));

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(
    <MemoryRouter>
      <ThemeProvider theme={theme}>{ui}</ThemeProvider>
    </MemoryRouter>
  );
}

const catalogs = {
  inspectores: [],
  motivos: [],
  rubros: [],
  tipos: [],
  contraproducencias: [],
  motivosComprobacion: [],
  itemsActaInspeccion: [],
};

const seguimientoPolicy = {
  mostrar_solicitud_carnet_manipulador: true,
  mostrar_subsanacion_notificacion: false,
  puede_editar_seguimiento: true,
};

const baseRow: IActuacionListItem = {
  id: 9,
  orden_trabajo_numero: "999",
  fecha_actuacion: "2026-06-01",
  rubro_nombre: "Carnicería",
  inspector1: "A",
  inspector2: null,
  inspector3: null,
  calle: "San Martín",
  numero: "10",
  tipo_actuacion: "Inspección",
  contraproducencia: "No",
  doc_nro: null,
  contrib_apellido: "López",
  contrib_nombre: "María",
  acta_inspeccion_num: "100",
  acta_notificacion_num: null,
  notificacion_motivo_1: null,
  notificacion_motivo_2: null,
  notificacion_motivo_3: null,
  acta_comprobacion_num: null,
  comprobacion_motivo: null,
  acta_clausura_num: null,
  acta_decomiso_num: null,
  decomiso_kilos_total: null,
  expediente_numero: null,
  expediente_anio: null,
  oficio_numero: null,
  oficio_anio: null,
  oficio_causa: null,
  ui_policy: seguimientoPolicy,
  seguimiento: {
    solicita_carnet_manipulador: true,
    telefono_contacto_solicitud_carnet: "381 555-0100",
  },
  domicilio: { calle: "Mitre", numero: "200", esquina: null },
  rubro: { nombre: "Carnicería" },
  contribuyente: { apellido: "López", nombre: "María" },
};

describe("ActuacionDetalleDialog seguimiento 1D", () => {
  it("modo Editar: toggles de carnet no están disabled", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Seguimiento de acta");
    expect(html).toContain("Domicilio del contribuyente");
    expect(html).toContain("Mitre 200");
    expect(html).toContain("López María");
    const disabledToggles = html.match(/MuiToggleButton-root Mui-disabled/g) ?? [];
    expect(disabledToggles.length).toBe(0);
  });

  it("modo Ver: toggles de carnet están disabled", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("MuiToggleButton-root Mui-disabled");
  });

  it("detailLoading no deshabilita toggles en edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        detailLoading
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    const disabledToggles = html.match(/MuiToggleButton-root Mui-disabled/g) ?? [];
    expect(disabledToggles.length).toBe(0);
  });
});
