import type {
  IComprobacionDocumentalResponse,
  OficioComprobacionItem,
} from "../../../api/actuacionesPendientesApi";
import { humanizarEstadoIniciador } from "./documentalLabelFormat";

/** Etiqueta compacta ``Oficio N/Año · Exp. N/Año``. */
export function oficioComprobacionEtiquetaCompacta(item: OficioComprobacionItem): string {
  const n = String(item.numero_oficio ?? "").trim();
  const a = item.anio != null ? String(item.anio) : "";
  const ofi = n || a ? `Oficio ${[n, a].filter(Boolean).join("/")}` : "Oficio —";
  const exN = String(item.expediente_numero ?? "").trim();
  const exA = item.expediente_anio != null ? String(item.expediente_anio) : "";
  if (!exN && !exA) return ofi;
  return `${ofi} · Exp. ${[exN, exA].filter(Boolean).join("/")}`;
}

/** Subtítulo opcional con estado de iniciador (solo si el payload lo trae). */
export function oficioComprobacionSubtituloIniciador(item: OficioComprobacionItem): string | null {
  if (item.iniciador_id == null && !item.iniciador_estado) return null;
  if (!item.iniciador_estado) return "Sin estado de iniciador";
  return `Iniciador ${humanizarEstadoIniciador(item.iniciador_estado)}`;
}

/** Indica si el ítem tiene bloque oficio + expediente de respuesta completo. */
export function oficioComprobacionTieneBloqueCompleto(item: OficioComprobacionItem): boolean {
  return item.expediente_id != null && String(item.expediente_numero ?? "").trim() !== "";
}

/**
 * Fallback legacy: si la lista viene vacía pero documental trae oficio + respuesta, sintetiza un ítem.
 */
export function mergeOficiosConLegacyDocumental(
  oficios: OficioComprobacionItem[],
  documental: IComprobacionDocumentalResponse | null
): OficioComprobacionItem[] {
  if (oficios.length > 0) return oficios;
  const ofi = documental?.oficio;
  const ex = documental?.expediente_respuesta;
  if (!ofi || !ex) return [];
  return [
    {
      id: ofi.id,
      numero_oficio: ofi.numero_oficio,
      anio: ofi.anio,
      causa: ofi.causa,
      fecha_oficio: ofi.fecha_oficio,
      juzgado_id: ofi.juzgado_id,
      tribunal: ofi.juzgado_nombre,
      expediente_id: ex.id,
      expediente_numero: ex.numero_expediente,
      expediente_anio: ex.anio,
      fecha_expediente_respuesta: ex.fecha_expediente,
    },
  ];
}

/** Arma un snapshot documental para editar/ver un oficio concreto de la lista. */
export function documentalDesdeOficioItem(
  base: IComprobacionDocumentalResponse,
  item: OficioComprobacionItem
): IComprobacionDocumentalResponse | null {
  if (!oficioComprobacionTieneBloqueCompleto(item)) return null;
  const tribunal =
    (item.tribunal ?? "").trim() ||
    (base.oficio?.juzgado_nombre && base.oficio.id === item.id ? base.oficio.juzgado_nombre : null);
  return {
    ...base,
    oficio: {
      id: item.id,
      numero_oficio: String(item.numero_oficio),
      anio: item.anio,
      fecha_oficio: item.fecha_oficio ?? null,
      causa: item.causa != null ? String(item.causa) : null,
      juzgado_id: item.juzgado_id ?? null,
      juzgado_nombre: tribunal,
    },
    expediente_respuesta: {
      id: item.expediente_id!,
      numero_expediente: String(item.expediente_numero),
      anio: String(item.expediente_anio ?? ""),
      fecha_expediente: item.fecha_expediente_respuesta ?? null,
      tipo_expediente: "RESPUESTA_OFICIO",
      oficio_id: item.id,
    },
  };
}
