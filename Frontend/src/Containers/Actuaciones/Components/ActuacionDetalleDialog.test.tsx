/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";

import { MemoryRouter } from "react-router-dom";

import { describe, expect, it, vi } from "vitest";

import { renderToStaticMarkup } from "react-dom/server";



import type { IActuacionListItem } from "../../../api/actuacionesListApi";

import { MENSAJE_BLOQUEO_EXPEDIENTE_EDICION } from "../utils/actuacionEditRules";

import { ActuacionDetalleDialog } from "./ActuacionDetalleDialog";



vi.mock("../../../components/feedback", () => ({

  useAppFeedback: () => ({

    warning: vi.fn(),

    success: vi.fn(),

    error: vi.fn(),

    info: vi.fn(),

  }),

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

  inspector2: null,

  inspector3: null,

  calle: "San Martín",

  numero: "450",

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

  establecimiento_operativo_id: 7,

  establecimiento_actuaciones_en_ficha: 3,

};



const catalogs = {

  inspectores: ["García", "López"],

  motivos: ["Falta de habilitación"],

  rubros: ["Carnicería"],

  tipos: ["Inspección"],

  contraproducencias: ["No", "Sí"],

  motivosComprobacion: ["Incumplimiento"],

};



describe("ActuacionDetalleDialog", () => {

  it("abre en modo vista con Editar e Imprimir sin IDs visibles", () => {

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

    expect(html).toContain("Ver actuación");

    expect(html).toContain("Editar");

    expect(html).toContain("Imprimir");

    expect(html).not.toContain("MuiAlert-standardError");

    expect(html).not.toContain("Cancelar");

  });



  it("modo edición con error de campo pinta helperText y no Alert inline de guardado", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        initialEditing

        draft={baseRow}

        fieldErrors={{ calle: "Calle inválida" }}

        saving={false}

        catalogs={catalogs}

        readOnlyColumns={[]}

        onClose={() => undefined}

        onDraftChange={() => undefined}

        onSave={() => undefined}

      />

    );

    expect(html).toContain("Calle inválida");

    expect(html).toContain("Mui-error");

    expect(html).not.toContain("MuiAlert-standardError");

    expect(html).not.toContain("Revisá los datos");

  });



  it("error en campo oculto no muestra CrudFormErrorSummary inline", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        initialEditing

        draft={baseRow}

        fieldErrors={{ notificacion_previa_num: "Obligatorio para REINSPECCIÓN." }}

        saving={false}

        catalogs={catalogs}

        readOnlyColumns={[]}

        onClose={() => undefined}

        onDraftChange={() => undefined}

        onSave={() => undefined}

      />

    );

    expect(html).not.toContain("MuiAlert-standardError");

    expect(html).not.toContain("Acta notificación previa");

  });



  it("modo edición muestra número o referencia para editar domicilio", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        initialEditing

        draft={{ ...baseRow, numero_tipo: "ESQUINA", numero: "Av. Corrientes" }}

        fieldErrors={{}}

        saving={false}

        catalogs={catalogs}

        readOnlyColumns={[]}

        numeroEditorLabel="Número o referencia"

        onClose={() => undefined}

        onDraftChange={() => undefined}

        onSave={() => undefined}

      />

    );

    expect(html).toContain("Número o referencia");

    expect(html).not.toContain("Ver establecimiento");

    expect(html).toContain("Esquina");

  });



  it("modo vista muestra Ver establecimiento cuando hay ficha vinculada", () => {

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

    expect(html).toContain("Ver establecimiento");

  });



  it("Actas labradas usa sección plana alineada a Cargar actuación", () => {

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

    expect(html).toContain("Actas labradas");

    expect(html).toContain("Datos de la actuación");

    expect(html).toContain("Domicilio y establecimiento");

  });



  it("bloqueo por expediente no renderiza Alert warning inline en el modal", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        draft={{ ...baseRow, notificacion_editable: false, comprobacion_editable: false }}

        fieldErrors={{}}

        saving={false}

        catalogs={catalogs}

        readOnlyColumns={[]}

        onClose={() => undefined}

        onDraftChange={() => undefined}

        onSave={() => undefined}

      />

    );

    expect(html).not.toContain("MuiAlert-standardWarning");

    expect(html).not.toContain(MENSAJE_BLOQUEO_EXPEDIENTE_EDICION);

  });



  it("modo edición no muestra botón Eliminar por acta", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        initialEditing

        draft={{

          ...baseRow,

          acta_notificacion_num: "200",

          notificacion_motivo_1: "Falta de habilitación",

          acta_decomiso_num: "300",

          decomiso_kilos_total: 5,

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

    expect(html).not.toContain(">Eliminar<");

  });



  it("comprobación sin motivo pinta campo en edición", () => {

    const html = render(

      <ActuacionDetalleDialog

        open

        disablePortal

        initialEditing

        draft={{ ...baseRow, acta_comprobacion_num: "900", comprobacion_motivo: "" }}

        fieldErrors={{ comprobacion_motivo: "Si cargás acta de comprobación, elegí un motivo de comprobación." }}

        saving={false}

        catalogs={catalogs}

        readOnlyColumns={[]}

        onClose={() => undefined}

        onDraftChange={() => undefined}

        onSave={() => undefined}

      />

    );

    expect(html).toContain("Si cargás acta de comprobación");

    expect(html).toContain("Mui-error");

    expect(html).not.toContain("MuiAlert-standardError");

  });

  it("reinspección por notificación deja contribuyente readonly en edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "REINSPECCION",
          documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
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
    expect(html).toContain('disabled=""');
    expect(html).not.toContain("Acta de notificación");
  });

  it("ratificación de clausura deja documento readonly en edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{ ...baseRow, tipo_actuacion: "RATIFICACION DE CLAUSURA" }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("N.º de documento");
    expect(html).toContain('disabled=""');
  });

  it("inspección normal permite editar contribuyente", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{ ...baseRow, tipo_actuacion: "INSPECCION" }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Apellido");
    expect(html).toContain("Motivos de notificación");
  });

  it("reinspección por oficio genérica no muestra layout normal ni notificación editable", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "REINSPECCION",
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
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
    expect(html).toContain('disabled=""');
    expect(html).not.toContain("Motivos de notificación");
    expect(html).not.toContain("Actas labradas");
  });

  it("ratificación clausura mantiene modo ratificación con circuito oficio", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "RATIFICACION DE CLAUSURA",
          resultado_cumplimiento_oficio: "CUMPLE",
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
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
    expect(html).toContain("¿Dio cumplimiento?");
    expect(html).not.toContain("Motivos de notificación");
    expect(html).toContain('disabled=""');
  });

  it("ratificación clausura con contra muestra campos de resultado operativo editables", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "RATIFICACION DE CLAUSURA",
          contraproducencia: "NO SE RATIFICÓ",
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
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
    expect(html).toContain("¿Dio cumplimiento?");
  });

  it("verificar e informar muestra pregunta de nueva inspección en edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "VERIFICAR E INFORMAR",
          realizo_nueva_inspeccion: false,
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
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
    expect(html).toContain("¿Realizó nueva inspección?");
  });

  it("verificar e informar sin actas persistidas no muestra bloque de actas", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "VERIFICAR E INFORMAR",
          acta_inspeccion_num: null,
          acta_notificacion_num: null,
          acta_comprobacion_num: null,
          acta_clausura_num: null,
          acta_decomiso_num: null,
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
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
    expect(html).not.toContain("Actas labradas");
  });

});

