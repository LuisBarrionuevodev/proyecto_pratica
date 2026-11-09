/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";

import { MemoryRouter } from "react-router-dom";
import { readFileSync } from "node:fs";

import { describe, expect, it, vi } from "vitest";

import { renderToStaticMarkup } from "react-dom/server";



import type { IActuacionListItem } from "../../../api/actuacionesListApi";

import { MENSAJE_BLOQUEO_EXPEDIENTE_EDICION } from "../utils/actuacionEditRules";

import {
  ActuacionDetalleDialog,
  actuacionDetalleDomicilioLinea,
  actuacionDetalleNumeroTipoVisible,
} from "./ActuacionDetalleDialog";



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

function lecturaMarkup(html: string): string {
  const start = html.indexOf('aria-label="Ficha de la actuación"');
  const end = html.indexOf('aria-label="Edición de la actuación"');
  return html.slice(start, end);
}

function occurrences(text: string, needle: string): number {
  return text.split(needle).length - 1;
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
  itemsActaInspeccion: [],

};

const itemsActaInspeccionCatalog = [
  { id: 1, codigo: "TIENE_BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" as const },
  { id: 2, codigo: "TIENE_SALON", nombre: "Salón", orden: 2, tipo_respuesta: "ESTADO" as const },
  { id: 3, codigo: "TIENE_DEPOSITO", nombre: "Depósito", orden: 3, tipo_respuesta: "ESTADO" as const },
  {
    id: 4,
    codigo: "TIENE_COCINA_MESA_TRABAJO",
    nombre: "Cocina / mesa de trabajo",
    orden: 4,
    tipo_respuesta: "ESTADO" as const,
  },
  { id: 5, codigo: "VAJILLA_MANTEL", nombre: "Vajilla / mantel", orden: 5, tipo_respuesta: "ESTADO" as const },
  {
    id: 6,
    codigo: "TIENE_HABILITACION",
    nombre: "Tiene habilitación",
    orden: 6,
    tipo_respuesta: "SI_NO" as const,
  },
];

const catalogsWithChecklist = {
  ...catalogs,
  itemsActaInspeccion: itemsActaInspeccionCatalog,
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
    expect(html).toContain("OT 12345 · 2026");

    expect(html).toContain("Editar");

    expect(html).toContain("Imprimir");

    expect(html).not.toContain("MuiAlert-standardError");

    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("Consulta de ficha operativa");
    expect(html).not.toContain(">Actuaciones<");

  });

  it("modo lectura presenta datos documentales sin inputs deshabilitados", () => {
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
    const start = html.indexOf('aria-label="Ficha de la actuación"');
    const end = html.indexOf('aria-label="Edición de la actuación"');
    const lectura = lecturaMarkup(html);
    expect(start).toBeGreaterThanOrEqual(0);
    expect(end).toBeGreaterThan(start);
    expect(lectura).toContain("Nombre de fantasía / razón social");
    expect(lectura).not.toContain("<input");
  });

  it("modo lectura muestra valores en campos documentales delimitados", () => {
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
    const lectura = lecturaMarkup(html);
    expect(lectura).toContain("Visita y actuación");
    expect(lectura).toContain("Establecimiento");
    expect(lectura).toContain("Domicilio");
    expect(lectura).toContain("Dirección");
    expect(lectura).toContain("Contribuyente");
    expect(lectura).toContain("Actas y resultado");
    expect(lectura).toContain("<label");
    expect(lectura).toContain("Fecha");
    expect(lectura).toContain("CUIT / DNI");
    expect(lectura).not.toContain("<input");
    expect(lectura).not.toContain('type="text"');
    expect(lectura).not.toContain("contenteditable");
    const iVisita = lectura.indexOf("Visita y actuación");
    const iEst = lectura.indexOf("Establecimiento");
    const iDom = lectura.indexOf("Domicilio");
    const iCont = lectura.indexOf("Contribuyente");
    const iActas = lectura.indexOf("Actas y resultado");
    expect(iVisita).toBeGreaterThan(-1);
    expect(iEst).toBeGreaterThan(iVisita);
    expect(iDom).toBeGreaterThan(iEst);
    expect(iCont).toBeGreaterThan(iDom);
    expect(iActas).toBeGreaterThan(iCont);
    expect(html.indexOf("Fotos y documentación")).toBeGreaterThan(html.indexOf("Actas y resultado"));
  });

  it("modo lectura muestra — en campos históricos vacíos y no admite edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          doc_nro: null,
          nombre_local: null,
          contrib_apellido: null,
          contrib_nombre: null,
          contribuyente: undefined,
          razon_social: null,
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
    const lectura = lecturaMarkup(html);
    expect(lectura).toContain("CUIT / DNI");
    expect(lectura).toContain("Nombre de fantasía / razón social");
    expect(lectura).toContain("—");
    expect(lectura).not.toContain("<input");
    expect(lectura).not.toContain("contenteditable");
    expect(lectura).not.toContain("<textarea");
  });

  it("modo lectura une calle y altura y oculta el tipo NUMERO", () => {
    const draft = {
      ...baseRow,
      calle: "República del Líbano",
      numero: "1709",
      numero_tipo: "NUMERO",
      domicilio: undefined,
    };
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
    const lectura = lecturaMarkup(html);
    expect(lectura).toContain("República del Líbano 1709");
    expect(lectura).not.toContain("Tipo de numeración");
    expect(actuacionDetalleDomicilioLinea(draft)).toBe("República del Líbano 1709");
    expect(actuacionDetalleNumeroTipoVisible("NÚMERO")).toBeNull();
  });

  it.each([
    ["ESQUINA", "Esquina"],
    ["SIN_NUMERO", "Sin número"],
  ])("modo lectura conserva el tipo especial %s", (numeroTipo, label) => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{ ...baseRow, numero_tipo: numeroTipo }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(lecturaMarkup(html)).toContain(label);
    expect(actuacionDetalleNumeroTipoVisible(numeroTipo)).toBe(label);
  });

  it("modo lectura omite contraproducencia vacía y documenta ausencia de actas", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          contraproducencia: null,
          acta_inspeccion_num: null,
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
    const lectura = lecturaMarkup(html);
    expect(lectura).not.toContain("Contraproducencia");
    expect(lectura).toContain("Sin actas labradas");
  });

  it("modo lectura presenta checklist y habilitación como texto, sin toggles", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          items_acta_inspeccion: [
            { id: 1, codigo: "TIENE_BANO", nombre: "Baño", estado: "BIEN" },
            {
              id: 6,
              codigo: "TIENE_HABILITACION",
              nombre: "Tiene habilitación",
              tipo_respuesta: "SI_NO",
              valor_si_no: true,
            },
          ],
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    const lectura = lecturaMarkup(html);
    expect(lectura).toContain("Condiciones verificadas");
    expect(lectura).toContain("Baño");
    expect(lectura).toContain("Familiar / Bien");
    expect(lectura).toContain("Tiene habilitación");
    expect(lectura).toContain("Sí");
    expect(lectura).not.toContain("MuiToggleButton-root");
    expect(lectura).not.toContain("<input");
  });

  it("VER muestra carácter, carnet, contrato y Baño Familiar / Bien en Actas labradas", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          caracter_persona_atendio: "ENCARGADO",
          posee_contrato_retiro_residuos_solidos_urbanos: false,
          solicita_carnet_manipulador: true,
          items_acta_inspeccion: [
            { id: 1, codigo: "TIENE_BANO", nombre: "Baño", estado: "BIEN" },
            { id: 2, codigo: "TIENE_SALON", nombre: "Salón", estado: "BIEN" },
          ],
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    const lectura = lecturaMarkup(html);
    expect(lectura).toContain("Carácter de quien atendió");
    expect(lectura).toContain("Encargado");
    expect(lectura).toContain("Solicitud de carnet de manipulador");
    expect(lectura).toContain("Contrato de retiro de residuos sólidos urbanos");
    expect(lectura).toContain("Familiar / Bien");
    expect(lectura).toContain("Salón");
    expect(lectura).toContain("Bien");
    expect(lectura).not.toContain("Atención en el establecimiento");
    const iActa = lectura.indexOf("N.º acta de inspección");
    const iCaracter = lectura.indexOf("Carácter de quien atendió");
    const iCarnet = lectura.indexOf("Solicitud de carnet de manipulador");
    const iContrato = lectura.indexOf("Contrato de retiro de residuos sólidos urbanos");
    const iCond = lectura.indexOf("Condiciones verificadas");
    expect(iActa).toBeGreaterThan(-1);
    expect(iCaracter).toBeGreaterThan(iActa);
    expect(iCarnet).toBeGreaterThan(iCaracter);
    expect(iContrato).toBeGreaterThan(iCarnet);
    expect(iCond).toBeGreaterThan(iContrato);
  });

  it("edición: atención visible y deshabilitada sin acta válida", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          acta_inspeccion_num: "",
          caracter_persona_atendio: "TITULAR",
          posee_contrato_retiro_residuos_solidos_urbanos: true,
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Carácter de quien atendió");
    expect(html).toContain("contrato de retiro de residuos sólidos urbanos");
    expect(html).toContain("Condiciones verificadas");
    expect(html).toContain("Mui-disabled");
    expect(html).toContain("TITULAR");
  });

  it("modo lectura consolida una sola vez antecedentes por oficio", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          acta_comprobacion_num: "000200",
          resultado_cumplimiento_oficio: "Cumple",
          notificacion_editable: false,
          comprobacion_editable: false,
          documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
          origen_reinspeccion_oficio: {
            comprobacion_acta_numero: "000200",
            comprobacion_acta_anio: 2025,
            expediente_numero: "EXP-9",
            expediente_anio: 2025,
            oficio_numero: "OF-8",
            oficio_anio: 2025,
            oficio_causa: "Control de cumplimiento",
          },
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
    const lectura = lecturaMarkup(html);
    expect(occurrences(lectura, "Reinspección por oficio")).toBe(1);
    expect(occurrences(lectura, "000200/2025")).toBe(1);
    expect(occurrences(lectura, "EXP-9/2025")).toBe(1);
    expect(occurrences(lectura, "OF-8/2025")).toBe(1);
    expect(occurrences(lectura, "Control de cumplimiento")).toBe(1);
    expect(occurrences(lectura, "Cumple")).toBe(1);
    expect(lectura).toContain("Comprobación de origen");
    expect(lectura).toContain("Expediente");
    expect(lectura).toContain("Oficio");
    expect(lectura).toContain("<label");
    expect(lectura).not.toContain("<input");
    expect(lectura).not.toContain("Edición en canal actas");
  });

  it("modo lectura consolida notificación de origen y faltas subsanadas", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          acta_notificacion_num: "000050",
          documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
          origen_reinspeccion_notificacion: {
            notificacion_acta_numero: "000050",
            notificacion_acta_anio: 2025,
          },
          seguimiento: {
            faltas_notificacion_subsanadas: true,
            notificacion_origen_numero: "000050",
          },
          ui_policy: {
            mostrar_solicitud_carnet_manipulador: false,
            mostrar_subsanacion_notificacion: true,
            puede_editar_seguimiento: true,
          },
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
    const lectura = lecturaMarkup(html);
    expect(occurrences(lectura, "Reinspección por notificación")).toBe(1);
    expect(occurrences(lectura, "000050/2025")).toBe(1);
    expect(occurrences(lectura, "Notificación de origen")).toBe(1);
    expect(occurrences(lectura, "Faltas subsanadas")).toBe(1);
    expect(lectura).toContain("<label");
    expect(lectura).not.toContain("<input");
    expect(lectura).not.toContain("MuiToggleButton-root");
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

  it("Ver establecimiento conserva cierre y navegación existentes", () => {
    const source = readFileSync(new URL("./ActuacionDetalleDialog.tsx", import.meta.url), "utf8");
    expect(source).toContain("onClose();");
    expect(source).toContain("navigate(`/establecimientos/${draft.establecimiento_operativo_id}`);");
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

    expect(html).toContain("Visita y actuación");

    expect(html).toContain("Establecimiento");
    expect(html).toContain("Domicilio");
    expect(html).toContain("Contribuyente");
    expect(html).toContain("Actas y resultado");

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

  it("FIX.9: RN realizada hidrata acta de inspección persistida en edición", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "REINSPECCION",
          contraproducencia: null,
          acta_inspeccion_num: "005032",
          acta_comprobacion_num: "000200",
          acta_clausura_num: null,
          acta_decomiso_num: null,
          acta_notificacion_num: null,
          documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
          origen_reinspeccion_notificacion: { notificacion_acta_numero: "000050" },
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
    expect(html).toContain("Actas labradas");
    expect(html).toContain("005032");
    expect(html).toContain("000200");
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
          acta_inspeccion_num: null,
          acta_notificacion_num: null,
          acta_comprobacion_num: null,
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
    expect(html).toContain("Resultado de la verificación");
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

  it("verificar con actas persistidas muestra inspección y notificación para quitar", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "VERIFICAR E INFORMAR",
          realizo_nueva_inspeccion: true,
          acta_inspeccion_num: "005032",
          acta_notificacion_num: "001234",
          notificacion_motivo_1: "Falta de habilitación",
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
    expect(html).toContain("Actas labradas");
    expect(html).toContain("005032");
    expect(html).toContain("001234");
    expect(html).toContain("Motivos de notificación");
  });

  it("verificar SI_INSPECCION muestra bloque completo de actas labradas", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          tipo_actuacion: "VERIFICAR E INFORMAR",
          realizo_nueva_inspeccion: true,
          contraproducencia: null,
          acta_inspeccion_num: null,
          acta_notificacion_num: null,
          acta_comprobacion_num: null,
          acta_clausura_num: null,
          acta_decomiso_num: null,
          can_edit_domicilio: false,
          can_edit_rubro: false,
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
    expect(html).toContain("Actas labradas");
    expect(html).toContain("N° acta de inspección");
    expect(html).toContain("N° acta de notificación");
    expect(html).toContain("Motivos de notificación");
    expect(html).toContain("N° acta de comprobación");
    expect(html).toContain("N° acta de clausura");
    expect(html).toContain("N° acta de decomiso");
  });

  it("modo VER muestra checklist readonly con estados persistidos y filas NONE", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          items_acta_inspeccion: [
            { id: 1, codigo: "TIENE_BANO", nombre: "Baño", estado: "BIEN" },
            { id: 3, codigo: "TIENE_DEPOSITO", nombre: "Depósito", estado: "OBSERVADO" },
          ],
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Condiciones verificadas");
    expect(html).toContain("Baño");
    expect(html).toContain("Familiar / Bien");
    expect(html).toContain("Depósito");
    expect(html).toContain("Salón");
    expect(html).toContain("Cocina / cuadra");
    expect(html).toContain("Vajilla / mantel");
    expect(html).toContain('value="BIEN"');
    expect(html).toContain('value="OBSERVADO"');
  });

  it("modo VER muestra cantidad de personas sin carnet con notificación de visita", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          acta_notificacion_num: "732394",
          notificacion_motivo_1: "Falta de habilitación",
          cantidad_personas_sin_carnet_sanidad: 2,
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Cantidad de personas sin carnet de sanidad");
    expect(html).toContain("2");
  });

  it("modo VER muestra 0 personas sin carnet cuando el valor persistido es cero", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          acta_notificacion_num: "732394",
          notificacion_motivo_1: "Falta de habilitación",
          cantidad_personas_sin_carnet_sanidad: 0,
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Cantidad de personas sin carnet de sanidad");
    expect(html).toContain(">0<");
  });

  it("modo edición hidrata checklist persistido al abrir", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          items_acta_inspeccion: [
            { id: 1, codigo: "TIENE_BANO", nombre: "Baño", estado: "BIEN" },
            { id: 3, codigo: "TIENE_DEPOSITO", nombre: "Depósito", estado: "OBSERVADO" },
          ],
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Condiciones verificadas");
    expect(html).toContain('value="BIEN"');
    expect(html).toContain('value="OBSERVADO"');
  });

  it("RN con notificación origen no muestra personas sin carnet en VER", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          tipo_actuacion: "REINSPECCION",
          acta_inspeccion_num: "005032",
          acta_notificacion_num: null,
          cantidad_personas_sin_carnet_sanidad: 3,
          documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
          origen_reinspeccion_notificacion: { notificacion_acta_numero: "000050" },
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogsWithChecklist}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).not.toContain("Cantidad de personas sin carnet de sanidad");
  });

  it("Inspector Editar datos (initialEditing): muestra Guardar y alerta de catálogos", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={{
          ...baseRow,
          ui_policy: {
            mostrar_solicitud_carnet_manipulador: false,
            mostrar_subsanacion_notificacion: false,
            puede_editar_seguimiento: false,
            puede_editar_datos_propios: true,
            puede_gestionar_fotos_propias: true,
          },
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        catalogsError="No se pudieron cargar: tipos de actuación."
        readOnlyColumns={[]}
        inspectorSelfService
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Guardar cambios");
    expect(html).toContain("tipos de actuación");
  });

  it("Inspector Mis trabajos: Cargar más fotos y sin Imprimir", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          ui_policy: {
            mostrar_solicitud_carnet_manipulador: false,
            mostrar_subsanacion_notificacion: false,
            puede_editar_seguimiento: false,
            puede_editar_datos_propios: true,
            puede_gestionar_fotos_propias: true,
          },
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        inspectorSelfService
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Cargar más fotos");
    expect(html).toContain("Editar datos");
    expect(html).not.toContain("Imprimir");
  });

  it("Inspector Ver trabajo: solo lectura sin acciones de edición ni carga", () => {
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        draft={{
          ...baseRow,
          ui_policy: {
            mostrar_solicitud_carnet_manipulador: false,
            mostrar_subsanacion_notificacion: false,
            puede_editar_seguimiento: false,
            puede_editar_datos_propios: true,
            puede_gestionar_fotos_propias: true,
          },
        }}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        inspectorSelfService
        inspectorVerTrabajoMode
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Ver trabajo");
    expect(html).not.toContain("Editar datos");
    expect(html).not.toContain("Cargar más fotos");
    expect(html).not.toContain("Guardar cambios");
    expect(html).not.toContain("Imprimir");
  });
});

