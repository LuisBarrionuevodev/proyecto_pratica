import type { IDetalleOperativoItem, IIniciadorOperativoCampos, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import { etiquetaTipoCorta, formatoNumeroConAnio, lineasIdentificadoresPendiente } from "../planificacion/utils/iniciadorDisplay";

type OperativoRow = IIniciadorOperativoCampos & {
  tipo_iniciador?: string | null;
  identificadores?: IRutaIniciadorPendienteRow["identificadores"];
  badges?: IRutaIniciadorPendienteRow["badges"];
};

/** Etiqueta de tipo priorizando `tipo_iniciador_label` del backend. */
export function tipoLabelOperativo(row: OperativoRow | undefined): string {
  if (!row) return "—";
  const label = row.tipo_iniciador_label?.trim();
  if (label) return label;
  if (row.tipo_iniciador) return etiquetaTipoCorta(row as IRutaIniciadorPendienteRow);
  return row.badges?.tipo_label?.trim() || "—";
}

function detalleDesdeItems(items: IDetalleOperativoItem[] | undefined): string | null {
  if (!items?.length) return null;
  return items.map((it) => `${it.label}: ${it.value}`).join(" · ");
}

/** Fallback local si el backend no envió `detalle_operativo_texto`. */
function detalleFallbackLocal(row: OperativoRow): string | null {
  const id = row.identificadores;
  const partes: string[] = [];

  const noti = formatoNumeroConAnio(id?.numero_notificacion, id?.anio_notificacion);
  if (noti) partes.push(`Notif.: ${noti}`);
  if (row.prorroga_texto?.trim()) partes.push(`Prórroga: ${row.prorroga_texto.trim()}`);
  else if (id?.prorroga_dias && id.prorroga_dias > 0) partes.push(`Prórroga: ${id.prorroga_dias} días`);

  const comp = formatoNumeroConAnio(id?.numero_comprobacion, id?.anio_comprobacion);
  if (comp) partes.push(`Acta comp.: ${comp}`);

  const exp = formatoNumeroConAnio(id?.numero_expediente, id?.anio_expediente ? Number(id.anio_expediente) : null);
  if (exp) partes.push(`Exp.: ${exp}`);

  const ofi = formatoNumeroConAnio(id?.numero_oficio, id?.anio_oficio);
  if (ofi) partes.push(`Oficio: ${ofi}`);

  const causa = row.causa?.trim() || id?.causa?.trim();
  if (causa) partes.push(`Causa: ${causa}`);

  const motivo = row.motivo_denuncia?.trim() || id?.motivo_denuncia?.trim();
  if (motivo) partes.push(`Motivo: ${motivo}`);

  if (partes.length) return partes.join(" · ");

  const lineas = lineasIdentificadoresPendiente(row as IRutaIniciadorPendienteRow);
  return lineas.length ? lineas.join(" · ") : null;
}

/** Línea compacta de detalle operativo para tabla, panel y export. */
export function detalleOperativoTexto(row: OperativoRow | undefined): string | null {
  if (!row) return null;
  const directo = row.detalle_operativo_texto?.trim();
  if (directo) return directo;
  const desdeItems = detalleDesdeItems(row.detalle_operativo_items);
  if (desdeItems) return desdeItems;
  return detalleFallbackLocal(row);
}

/** Convierte ítem de ruta en fila de iniciador para lookup en panel asignado. */
export function iniciadorPendienteDesdeItemMin(item: IRutaItemMin): IRutaIniciadorPendienteRow {
  return {
    id: item.iniciador_ruta_id,
    tipo_iniciador: item.tipo_iniciador ?? "",
    estado_iniciador: item.estado_ruta_item,
    fecha_origen: null,
    prioridad: item.prioridad ?? null,
    turno_sugerido: null,
    domicilio_texto: item.domicilio_texto ?? null,
    distrito_id: item.distrito_id ?? null,
    distrito_nombre: item.distrito_nombre ?? null,
    rubro_nombre: item.rubro_nombre ?? null,
    nombre_fantasia: item.nombre_fantasia ?? null,
    angulo_esquina: item.angulo_esquina ?? null,
    domicilio: {
      id: item.domicilio_id ?? null,
      calle: null,
      numero: null,
      distrito_id: item.distrito_id ?? null,
      distrito_nombre: item.distrito_nombre ?? null,
      barrio_id: null,
      rubro: item.rubro_nombre ?? null,
    },
    origen: {
      tipo: null,
      denuncia_id: null,
      relevamiento_id: null,
      notificacion_id: null,
      oficio_id: null,
      actuacion_id: item.actuacion_id ?? null,
    },
    observaciones: null,
    tipo_iniciador_label: item.tipo_iniciador_label ?? null,
    prioridad_label: item.prioridad_label ?? null,
    prioridad_categoria: item.prioridad_categoria,
    detalle_operativo_items: item.detalle_operativo_items,
    detalle_operativo_texto: item.detalle_operativo_texto ?? null,
    motivo_denuncia: item.motivo_denuncia ?? null,
    causa: item.causa ?? null,
    prorroga_texto: item.prorroga_texto ?? null,
    badges: item.badges,
    identificadores: item.identificadores,
    lat: item.lat ?? null,
    lng: item.lng ?? null,
  };
}

/** Mapa iniciador_id → fila operativa combinando pool e ítems asignados. */
export function buildIniciadorByIdMap(
  poolRowsById: Record<number, IRutaIniciadorPendienteRow>,
  itemsActivos: IRutaItemMin[]
): Record<number, IRutaIniciadorPendienteRow> {
  const map = { ...poolRowsById };
  for (const it of itemsActivos) {
    const fromItem = iniciadorPendienteDesdeItemMin(it);
    const existing = map[it.iniciador_ruta_id];
    map[it.iniciador_ruta_id] = existing ? { ...fromItem, ...existing } : fromItem;
  }
  return map;
}
