import { describe, expect, it } from "vitest";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import {
  rutasLabelEstadoRuta,
  rutasLabelFilaRutaListado,
  rutasLabelTurno,
} from "./rutasEmptyViewDisplay";

function ruta(partial: Partial<IRutaTrabajo> = {}): IRutaTrabajo {
  return {
    id: 1,
    fecha: "2026-03-15",
    turno: "MANIANA",
    estado_ruta: "BORRADOR",
    numero: 42,
    observaciones: null,
    created_by_user_id: 1,
    created_at: null,
    updated_at: null,
    ...partial,
  };
}

describe("rutasEmptyViewDisplay", () => {
  it("formatea turno y estado institucional", () => {
    expect(rutasLabelTurno("TARDE")).toBe("Tarde");
    expect(rutasLabelEstadoRuta("PUBLICADA")).toBe("Publicada");
  });

  it("arma etiqueta de fila desktop con número y turno", () => {
    expect(rutasLabelFilaRutaListado(ruta())).toContain("Ruta 42");
    expect(rutasLabelFilaRutaListado(ruta())).toContain("Mañana");
    expect(rutasLabelFilaRutaListado(ruta({ estado_ruta: "PUBLICADA" }))).not.toContain("PUBLICADA");
  });
});
