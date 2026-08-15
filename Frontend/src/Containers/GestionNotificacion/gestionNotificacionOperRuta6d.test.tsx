import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  debeMostrarGestionarDesdeRutaTrabajo,
  MENSAJE_GESTIONAR_DESDE_RUTA_TRABAJO,
} from "../../utils/operRutaPoolAcciones";
import { formatEstadoOperativoPoolLabel } from "../../utils/formatEstadoOperativoPoolLabel";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.6D", () => {
  it("en_ruta_borrador muestra caption Gestionar desde Ruta de Trabajo", () => {
    expect(
      debeMostrarGestionarDesdeRutaTrabajo({ estado_operativo_pool: "en_ruta_borrador", iniciador_id: 1 })
    ).toBe(true);
    const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
    expect(cell).toContain("MENSAJE_GESTIONAR_DESDE_RUTA_TRABAJO");
    expect(cell).toContain("oper-ruta-gestionar-desde-ruta");
  });

  it("chip en_ruta_borrador mantiene label En grupo asignado", () => {
    expect(
      formatEstadoOperativoPoolLabel({
        estado_operativo_pool: "en_ruta_borrador",
        ruta_fecha: "2026-08-24",
        ruta_numero: 100,
        ruta_turno: "MANIANA",
      })
    ).toContain("En grupo asignado");
  });

  it("Asignación no renderiza PoolDelDiaPanel compact duplicado", () => {
    const view = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
    expect(view).not.toContain("PoolDelDiaPanel");
    expect(view).toContain("TablaIniciadoresPendientes");
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain("asignacion-eliminar-del-pool");
  });

  it("GestionNotificacion bloquea prórroga en pool/ruta", () => {
    const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
    expect(page).toContain("estaBloqueadoParaGestionDocumental");
    expect(page).toContain("MENSAJE_BLOQUEO_GESTION_POOL_RUTA");
  });

  it("Comprobaciones bloquea gestionar oficio en pool/ruta", () => {
    const page = read("src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
    expect(page).toContain("estaBloqueadoParaGestionDocumental");
    expect(page).toContain("MENSAJE_BLOQUEO_GESTION_POOL_RUTA");
  });
});
