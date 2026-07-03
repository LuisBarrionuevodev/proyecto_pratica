import { describe, expect, it } from "vitest";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import {
  buildCompletarTrabajoCierreBody,
  buildCompletarTrabajoCierreBodyFromInline,
  EMPTY_COMPLETAR_FORM,
} from "./buildCompletarTrabajoCierreBody";

const rowMonteagudo = {
  ruta_item_id: 1,
  calle: "monteagudo",
  calle_key: "monteagudo",
  calle_normalizada: "Dr Bernardo Monteagudo",
  calle_estado: "OK",
} as ICompletarTrabajoPendienteRow;

describe("buildCompletarTrabajoCierreBody domicilio", () => {
  it("envía calle/número editados sin campos de geocode", () => {
    const body = buildCompletarTrabajoCierreBody({
      ...EMPTY_COMPLETAR_FORM,
      calle: "monteagudo corregido",
      numero: "150",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    });
    expect(body.calle).toBe("monteagudo corregido");
    expect(body.numero).toBe("150");
    expect(body.numero_tipo).toBe("NUMERO");
    expect(body).not.toHaveProperty("lat");
    expect(body).not.toHaveProperty("lng");
    expect(body).not.toHaveProperty("latitude");
    expect(body).not.toHaveProperty("longitude");
    expect(body).not.toHaveProperty("geocode_status");
    expect(body).not.toHaveProperty("geocode_hash");
  });

  it("no manda calle_key ni calle sin editar", () => {
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowMonteagudo,
      { calle: "Dr Bernardo Monteagudo", numero: "100" },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBe("100");
  });

  it("no manda esquina técnica sin editar", () => {
    const rowEsquina = {
      ...rowMonteagudo,
      numero_tipo: "ESQUINA",
      numero: "santiago del estero",
      esquina_key: "santiago del estero",
      esquina_normalizada: "Santiago del Estero",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowEsquina,
      {
        calle: "Dr Bernardo Monteagudo",
        numero: "Santiago del Estero",
        numero_tipo: "ESQUINA",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBeUndefined();
    expect(body.numero_tipo).toBeUndefined();
  });
});
