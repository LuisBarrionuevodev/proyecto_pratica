import type { GestionDomiciliosStatusOperativo } from "../../../../api/gestionDomiciliosApi";
import type { MapaDomiciliosGeolocalizacionActionVariant } from "./components/MapaDomiciliosGeolocalizacionLista";
import type { MapaDomiciliosGeolocalizacionFilterVariant } from "./components/MapaDomiciliosGeolocalizacionFiltro";

export type MapaDomiciliosGeolocalizacionViewProps = {
  title?: string;
  subtitle?: string;
  showHeader?: boolean;
  filterVariant?: MapaDomiciliosGeolocalizacionFilterVariant;
  actionVariant?: MapaDomiciliosGeolocalizacionActionVariant;
  showDetailPanel?: boolean;
  defaultStatus?: GestionDomiciliosStatusOperativo;
};
