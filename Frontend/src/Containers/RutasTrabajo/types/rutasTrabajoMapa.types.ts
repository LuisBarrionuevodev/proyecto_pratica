import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import type { GuardarOtItemResult } from "../hooks/useRutaTrabajoBorradorActions";

/** Punto en el mapa (cuando existan coordenadas en datos). */
export type RutaMapaMarker = {
  itemId: number;
  grupoId: number;
  /** Código estable en mapa (G1, G2…) para B/N y leyenda implícita. */
  grupoCodigo: string;
  /** Índice para anillo del pin (contraste sin color). */
  grupoStyleIndex: number;
  nombreGrupo: string;
  orden: number;
  lat: number;
  lng: number;
  etiqueta: string;
  color: string;
  rubroNombre?: string | null;
  distritoNombre?: string | null;
  /** Código crudo (solo uso interno si hiciera falta). */
  geoStatus?: string | null;
  /** Texto para popup / UI. */
  geoStatusLabel?: string | null;
  ordenTrabajoLabel?: string | null;
  tipoIniciadorLabel?: string | null;
};

/** Polilínea por grupo (orden de visita). Positions en [lat, lng] para react-leaflet. */
export type RutaMapaPolyline = {
  grupoId: number;
  grupoCodigo: string;
  grupoNombreCorto: string;
  color: string;
  positions: [number, number][];
  /** Patrón de trazo distinto por grupo (legible en B/N). */
  dashArray?: string;
  weight: number;
};

/** Item enriquecido para panel y mapa. */
export type RutaMapaItemVista = {
  itemId: number;
  iniciadorRutaId: number;
  orden: number;
  etiqueta: string;
  lat: number | null;
  lng: number | null;
  rubroNombre?: string | null;
  distritoNombre?: string | null;
  geoStatus?: string | null;
  geoStatusLabel?: string | null;
  ordenTrabajoLabel?: string | null;
  /** Humanizado: prioriza `IRutaItemMin.tipo_iniciador` (detail); si falta, pool de planificación. */
  tipoIniciadorLabel?: string | null;
};

/** Inspector del grupo para chips / lista en panel. */
export type RutaMapaInspectorFila = {
  inspectorId: number;
  nombre: string;
  legajo: string | null;
};

/** Grupo con datos derivados para UI mapa. */
export type RutaMapaGrupoVista = {
  id: number;
  nombre: string;
  color: string;
  estado: string | null;
  /** @deprecated Preferir `inspectoresFilas` en UI nueva. */
  inspectoresResumen: string;
  inspectoresFilas: RutaMapaInspectorFila[];
  itemCount: number;
  items: RutaMapaItemVista[];
};

/** Métricas agregadas para la vista Mapa final (solo lectura). */
export type RutaMapaResumenTerritorial = {
  totalItems: number;
  itemsConCoordenadas: number;
  /** Distritos distintos con nombre en ítems (cuando exista en datos). */
  distritosCubiertos: string[];
  /** Texto breve para lectura de cobertura / dispersión. */
  hintCobertura: string | null;
};

export type UseRutaMapaResult = {
  gruposVista: RutaMapaGrupoVista[];
  markers: RutaMapaMarker[];
  polylines: RutaMapaPolyline[];
  mapCenter: [number, number];
  mapZoom: number;
  tieneCoordenadas: boolean;
  avisoCoordenadas: string | null;
  resumenTerritorial: RutaMapaResumenTerritorial;
};

export type RutasMapaOperativoViewProps = {
  ruta: IRutaTrabajo | null;
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  /** Vuelve a la etapa Asignación (paso 2 del flujo). */
  onVolverAsignacion: () => void;
  onPublicarRuta?: () => void | Promise<void>;
  /** Ruta en BORRADOR con datos listos; false deshabilita el botón. */
  canPublish?: boolean;
  /** Tooltip del botón Publicar (condiciones pendientes o ayuda). */
  publicarTooltip?: string;
  /** Condiciones que impiden publicar (vacío = listo). */
  publicarBlockers?: string[];
  /** Muestra estado de carga en el botón de publicar. */
  publishingRuta?: boolean;
  /** Misma gestión liviana que TABLA (comparte handlers con el contenedor). */
  detailLoading?: boolean;
  /** Abre el modal de inspectores del grupo (Mapa final y Asignación). */
  onEditarInspectores?: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo?: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem?: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem?: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem?: (item: IRutaItemMin, numeroOt: string) => GuardarOtItemResult | Promise<GuardarOtItemResult>;
  /**
   * Preview histórica: ruta no BORRADOR (p. ej. PUBLICADA). Solo lectura para edición/publicación;
   * documentación PDF oficial desde `documentos/` (resumen + órdenes de salida).
   */
  vistaHistoricaReadOnly?: boolean;
  /** Con `vistaHistoricaReadOnly`, vuelve al listado inicial (borradores / publicadas). */
  onVolverAlListado?: () => void;
};
