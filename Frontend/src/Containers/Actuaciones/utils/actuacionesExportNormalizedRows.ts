import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { contribuyenteBandejaLabel } from "../../../utils/contribuyenteBandejaText";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";

function cell(value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  const s = String(value).trim();
  return s;
}

function joinParts(parts: (string | null | undefined)[], sep = "; "): string {
  return parts.map((p) => (p ?? "").trim()).filter(Boolean).join(sep);
}

function parseAnioMes(fecha: string | null | undefined): { anio: string; mes: string } {
  const f = (fecha ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(f)) return { anio: "", mes: "" };
  const [y, m] = f.slice(0, 10).split("-");
  return { anio: y, mes: m };
}

function inspectoresText(row: IActuacionListItem): string {
  const texto = row.inspectores_texto?.trim();
  if (texto) return texto;
  const fromArr = row.inspectores?.filter((s): s is string => Boolean(s?.trim()));
  if (fromArr?.length) return fromArr.map((s) => s.trim()).join(", ");
  return joinParts([row.inspector1, row.inspector2, row.inspector3], ", ");
}

function expedienteText(row: IActuacionListItem): string {
  const n = (row.expediente_numero ?? "").trim();
  if (!n) return "";
  const a = row.expediente_anio != null ? String(row.expediente_anio) : "";
  return a ? `${n}/${a}` : n;
}

function oficioText(row: IActuacionListItem): string {
  const n = (row.oficio_numero ?? "").trim();
  if (!n) return "";
  const a = row.oficio_anio != null ? String(row.oficio_anio) : "";
  return a ? `${n}/${a}` : n;
}

export type ActuacionNormalizedExcelRow = Record<string, string | number>;

/**
 * Filas planas para Excel administrativo (columnas atómicas, sin chips ni JSX).
 */
export function buildActuacionesNormalizedExcelRows(
  items: IActuacionListItem[]
): ActuacionNormalizedExcelRow[] {
  return items.map((row) => {
    const { anio, mes } = parseAnioMes(row.fecha_actuacion);
    const domicilioLinea = formatActuacionListDomicilioLinea(row).trim();

    return {
      "Fecha actuación": cell(row.fecha_actuacion),
      Año: anio,
      Mes: mes,
      "Orden de trabajo": cell(row.orden_trabajo_numero),
      "Tipo actuación": cell(row.tipo_actuacion),
      Contraproducencia: cell(row.contraproducencia),
      Domicilio: domicilioLinea,
      Calle: cell(row.calle ?? row.calle_mostrar ?? row.calle_ingresada),
      Número: cell(row.numero ?? row.numero_esquina),
      Rubro: cell(row.rubro_nombre),
      Contribuyente: contribuyenteBandejaLabel(
        row.contrib_apellido,
        row.contrib_nombre,
        row.razon_social
      ),
      Documento: cell(row.doc_nro),
      Inspectores: inspectoresText(row),
      "Acta inspección Nº": cell(row.acta_inspeccion_num),
      "Acta notificación Nº": cell(row.acta_notificacion_num),
      "Motivos notificación": joinParts([
        row.notificacion_motivo_1,
        row.notificacion_motivo_2,
        row.notificacion_motivo_3,
      ]),
      "Acta comprobación Nº": cell(row.acta_comprobacion_num),
      "Motivo comprobación": cell(row.comprobacion_motivo),
      "Clausura Nº": cell(row.acta_clausura_num),
      "Decomiso Nº": cell(row.acta_decomiso_num),
      "Kilos decomisados": cell(row.decomiso_kilos_total),
      Expediente: expedienteText(row),
      Oficio: oficioText(row),
      "Causa oficio": cell(row.oficio_causa),
      "Resultado cumplimiento oficio": cell(row.resultado_cumplimiento_oficio),
    };
  });
}
