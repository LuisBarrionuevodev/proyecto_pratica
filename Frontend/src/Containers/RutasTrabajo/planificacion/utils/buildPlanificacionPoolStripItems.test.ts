import { describe, expect, it } from "vitest";

import {
  buildPlanificacionPoolStripItems,
  countPlanificacionPoolStripItems,
} from "./buildPlanificacionPoolStripItems";
import type { IRutaGrupoMin, IRutaItemMin } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";

describe("buildPlanificacionPoolStripItems", () => {
  const poolLibre: IRutaPoolDiaRow = {
    pool_id: 10,
    fecha: "2026-08-06",
    estado: "EN_POOL",
    iniciador_id: 1,
    iniciador_ruta_id: 1,
    domicilio_texto: "Av. Test 123",
    distrito_nombre: "Dto. 10",
    tipo_iniciador_label: "Relevamiento",
  };

  const poolEnGrupo: IRutaPoolDiaRow = {
    ...poolLibre,
    pool_id: 11,
    iniciador_id: 102,
    iniciador_ruta_id: 102,
    ruta_item_id: 500,
    domicilio_texto: "Calle 2",
    tipo_iniciador_label: "Notificación",
  };

  const itemGrupo: IRutaItemMin = {
    id: 500,
    ruta_grupo_id: 7,
    iniciador_ruta_id: 102,
    domicilio_texto: "Calle 2",
    distrito_nombre: "Dto. 10",
    tipo_iniciador_label: "Notificación",
  } as IRutaItemMin;

  const grupos: IRutaGrupoMin[] = [{ id: 7, nombre: "Grupo 1", inspectores: [] }];

  it("muestra ítems en pool libre y en grupo deduplicados", () => {
    const items = buildPlanificacionPoolStripItems({
      poolItems: [poolLibre, poolEnGrupo],
      grupos,
      itemsActivos: [itemGrupo],
    });
    expect(items).toHaveLength(2);
    const pool = items.find((i) => i.iniciadorId === 1);
    const grupo = items.find((i) => i.iniciadorId === 102);
    expect(pool?.estado).toBe("pool");
    expect(pool?.estadoLabel).toBe("En pool");
    expect(pool?.puedeQuitar).toBe(true);
    expect(grupo?.estado).toBe("grupo");
    expect(grupo?.estadoLabel).toBe("En grupo");
    expect(grupo?.grupoNombre).toBe("Grupo 1");
    expect(grupo?.puedeQuitar).toBe(false);
  });

  it("cuenta en pool y en grupo", () => {
    const items = buildPlanificacionPoolStripItems({
      poolItems: [poolLibre, poolEnGrupo],
      grupos,
      itemsActivos: [itemGrupo],
    });
    expect(countPlanificacionPoolStripItems(items)).toEqual({ enPool: 1, enGrupo: 1, total: 2 });
  });
});
