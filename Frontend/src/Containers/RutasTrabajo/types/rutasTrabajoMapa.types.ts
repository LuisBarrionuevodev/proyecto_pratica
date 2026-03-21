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

export type UseRutaMapaResult = {
  gruposVista: RutaMapaGrupoVista[];
  markers: RutaMapaMarker[];
  polylines: RutaMapaPolyline[];
  mapCenter: [number, number];
  mapZoom: number;
  tieneCoordenadas: boolean;
  avisoCoordenadas: string | null;
};

export type RutasMapaOperativoViewProps = {
  ruta: IRutaTrabajo | null;
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onVolverPlanificacion: () => void;
  onPublicarRuta?: () => void | Promise<void>;
  /** Sin endpoint de publicación: false (botón deshabilitado). */
  canPublish?: boolean;
};
