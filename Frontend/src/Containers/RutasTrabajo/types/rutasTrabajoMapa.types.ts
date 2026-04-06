import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";

/** Punto en el mapa (cuando existan coordenadas en datos). */
export type RutaMapaMarker = {
  itemId: number;
  grupoId: number;
  orden: number;
  lat: number;
  lng: number;
  etiqueta: string;
  color: string;
  rubroNombre?: string | null;
  distritoNombre?: string | null;
  geoStatus?: string | null;
  ordenTrabajoLabel?: string | null;
};

/** Polilínea por grupo (orden de visita). Positions en [lat, lng] para react-leaflet. */
export type RutaMapaPolyline = {
  grupoId: number;
  color: string;
  positions: [number, number][];
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
  ordenTrabajoLabel?: string | null;
};

/** Grupo con datos derivados para UI mapa. */
export type RutaMapaGrupoVista = {
  id: number;
  nombre: string;
  color: string;
  estado: string | null;
  inspectoresResumen: string;
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
  /** Muestra estado de carga en el botón de publicar. */
  publishingRuta?: boolean;
  /** Misma gestión liviana que TABLA (comparte handlers con el contenedor). */
  detailLoading?: boolean;
  /** Reservados por compatibilidad; la Vista Mapa final no gestiona asignación (solo lectura + publicar). */
  onEditarInspectores?: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo?: (grupo: IRutaGrupoMin) => void | Promise<void>;
  onMoverItem?: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem?: (item: IRutaItemMin) => void | Promise<void>;
  onGuardarOtItem?: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
};
