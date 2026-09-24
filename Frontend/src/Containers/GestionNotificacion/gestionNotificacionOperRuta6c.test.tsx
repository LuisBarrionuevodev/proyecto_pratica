import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { formatEstadoOperativoPoolLabel } from "../../utils/formatEstadoOperativoPoolLabel";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.6C", () => {
  it("modal inicializa con pool_fecha y ruta reales, no hoy por defecto", () => {
    const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");
    expect(dialog).toContain("operContext");
    expect(dialog).toContain("pool_fecha");
    expect(dialog).toContain("ruta_trabajo_id");
    expect(dialog).toContain('estado === "en_pool"');
    expect(dialog).toContain('estado === "en_ruta_borrador"');
  });

  it("chip en_pool muestra En ruta con contexto", () => {
    expect(
      formatEstadoOperativoPoolLabel({
        estado_operativo_pool: "en_pool",
        pool_fecha: "2026-02-26",
        ruta_numero: 100,
        ruta_turno: "MANIANA",
      })
    ).toBe("En ruta (26/02/2026 - Ruta 100 - Turno Mañana)");
  });

  it("chip en_ruta_borrador muestra En grupo asignado", () => {
    expect(
      formatEstadoOperativoPoolLabel({
        estado_operativo_pool: "en_ruta_borrador",
        ruta_fecha: "2026-08-24",
        ruta_numero: 100,
        ruta_turno: "MANIANA",
      })
    ).toBe("En grupo asignado (24/08/2026 - Ruta 100 - Turno Mañana)");
  });

  it("acciones pool usan refresh silencioso", () => {
    const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
    expect(cell).toContain("silent: true");
    const notif = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
    expect(notif).toContain("silent?: boolean");
    const comp = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
    expect(comp).toContain("silent?: boolean");
  });

  it("Asignación muestra tabla pool con Eliminar del pool", () => {
    const view = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
    expect(view).toContain("TablaIniciadoresPendientes");
    expect(view).not.toContain("PoolDelDiaPanel");
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain("Eliminar del pool");
    expect(tabla).toContain("asignacion-eliminar-del-pool");
  });

  it("eliminar ítem de grupo refresca pool", () => {
    const index = read("src/Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("onAfterDeleteItem: syncPoolTrasQuitarItem");
    expect(index).toContain("refreshPool(ruta?.fecha");
  });
});
