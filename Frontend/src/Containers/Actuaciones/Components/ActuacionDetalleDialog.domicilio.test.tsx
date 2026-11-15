/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { fetchCallesCatalogo } from "../../../api/geolocalizacionApi";
import {
  ActuacionDetalleDialog,
  actuacionDetalleDomicilioLinea,
} from "./ActuacionDetalleDialog";

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

const baseRow: IActuacionListItem = {
  id: 42,
  orden_trabajo_numero: "12345",
  fecha_actuacion: "2026-05-10",
  rubro_nombre: "Carnicería",
  inspector1: "García",
  inspector2: "López",
  inspector3: null,
  calle: "San Martín",
  numero: "450",
  numero_tipo: "NUMERO",
  tipo_actuacion: "Inspección",
  contraproducencia: "No",
  doc_nro: "30123456",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
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
};

const catalogs = {
  inspectores: ["García", "López"],
  motivos: ["Falta de habilitación"],
  rubros: ["Carnicería"],
  tipos: ["Inspección"],
  contraproducencias: ["No", "Sí"],
  motivosComprobacion: ["Incumplimiento"],
  itemsActaInspeccion: [],
};

describe("ActuacionDetalleDialog domicilio sin catálogo", () => {
  it("calle es input libre y no usa Autocomplete de calles", () => {
    vi.mocked(fetchCallesCatalogo).mockClear();
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
    expect(html).toContain("Calle");
    expect(html).toContain("Esquina");
    expect(html).toContain("Número o referencia");
    expect(fetchCallesCatalogo).not.toHaveBeenCalled();
  });

  it("PR7.15c: domicilio editable muestra calle y número como value habilitados", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          can_edit_domicilio: true,
          calle: "Mendoza",
          calle_normalizada: "Av. Mendoza",
          numero: "500",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain('value="Mendoza"');
    expect(html).toContain('value="500"');
  });

  it("ACT-EDIT.1C: Denuncia con contribuyente hidratado no muestra reinspección ni pide identidad", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "INSPECCION",
          can_edit_domicilio: false,
          can_edit_rubro: true,
          contribuyente: { apellido: "Pérez", nombre: "Juan" },
          contrib_apellido: "Pérez",
          contrib_nombre: "Juan",
          calle: "San Martín",
          numero: "100",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain('value="San Martín"');
    expect(html).toContain('value="100"');
    expect(html).not.toContain("La actuación proviene de una reinspección");
    expect(html).not.toContain("Si cargás domicilio, debés cargar contribuyente.");
  });

  it("ACT-EDIT.1B: Inspección de Relevamiento no muestra mensaje de reinspección", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "INSPECCION",
          can_edit_domicilio: false,
          can_edit_rubro: true,
          domicilio_edit_blocked_reason:
            "La actuación proviene de una reinspección y el domicilio no puede modificarse.",
          documentacion_contexto: { circuito: "DESCONOCIDO", propia: {} },
          calle: "Mendoza",
          numero: "500",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain('value="Mendoza"');
    expect(html).toContain('value="500"');
    expect(html).not.toContain("La actuación proviene de una reinspección");
  });

  it("ACT-EDIT.1: actuación base con iniciador RN derivado habilita calle y número", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "INSPECCION",
          can_edit_domicilio: false,
          can_edit_rubro: false,
          domicilio_edit_blocked_reason:
            "La actuación proviene de una reinspección y el domicilio no puede modificarse.",
          documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
          calle: "Mendoza",
          numero: "500",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain('value="Mendoza"');
    expect(html).toContain('value="500"');
    expect(html).not.toContain("La actuación proviene de una reinspección");
  });

  it("PR7.15c: domicilio bloqueado deshabilita calle y número", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "REINSPECCION",
          can_edit_domicilio: false,
          domicilio_edit_blocked_reason:
            "La actuación proviene de una reinspección y el domicilio no puede modificarse.",
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("reinspección");
    expect(html).toContain("disabled");
  });
});

describe("ActuacionDetalleDialog Ver actuación domicilio vigente", () => {
  it("no usa calle_raw anidada cuando hay calle normalizada vigente", () => {
    const draft: IActuacionListItem = {
      ...baseRow,
      calle: "Corrientes",
      calle_raw: "Corrientes",
      calle_normalizada: "Ejército del Norte",
      calle_estado: "OK",
      numero: "602",
      numero_tipo: "NUMERO",
      domicilio: { calle: "Corrientes", numero: "602" },
    };
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("Ejército del Norte 602");
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={draft}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Ejército del Norte 602");
    expect(html).not.toContain("Corrientes 602");
  });

  it("reinspección por notificación muestra la dirección vigente, no el raw anidado", () => {
    const draft: IActuacionListItem = {
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      calle: "Corrientes",
      calle_normalizada: "Ejército del Norte",
      calle_estado: "OK",
      numero: "602",
      domicilio: { calle: "Corrientes", numero: "602" },
    };
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("Ejército del Norte 602");
  });

  it("reinspección por oficio muestra la dirección vigente, no el raw anidado", () => {
    const draft: IActuacionListItem = {
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      calle: "raw oficio",
      calle_normalizada: "Maipú",
      calle_estado: "OK",
      numero: "120",
      domicilio: { calle: "raw oficio", numero: "120" },
    };
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("Maipú 120");
  });

  it("intersección usa calle y esquina vigentes", () => {
    const draft: IActuacionListItem = {
      ...baseRow,
      calle: "vieja",
      calle_normalizada: "San Martín",
      calle_estado: "OK",
      numero_tipo: "ESQUINA",
      numero: "slug-mitre",
      numero_esquina: "Mitre",
      esquina_normalizada: "Mitre",
      domicilio: { calle: "vieja", numero: "slug-mitre", esquina: "otra raw" },
    };
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("San Martín Y Mitre");
  });

  it("histórico incompleto no inventa dirección", () => {
    const draft: IActuacionListItem = {
      ...baseRow,
      calle: null,
      numero: null,
      numero_tipo: null,
      calle_normalizada: null,
      domicilio: { calle: null, numero: null, esquina: null },
    };
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("—");
  });
});
