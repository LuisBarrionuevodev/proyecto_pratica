import { useEffect } from "react";
import { useMap } from "react-leaflet";

type PlanificacionMapInvalidateSizeProps = {
  active: boolean;
};

/**
 * Recalcula dimensiones del mapa Leaflet al volver visible (p. ej. Planificación tras Asignación).
 */
export function PlanificacionMapInvalidateSize({ active }: PlanificacionMapInvalidateSizeProps) {
  const map = useMap();

  useEffect(() => {
    if (!active) return;
    const run = () => map.invalidateSize({ animate: false });
    run();
    const t1 = window.setTimeout(run, 60);
    const t2 = window.setTimeout(run, 280);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [map, active]);

  return null;
}
