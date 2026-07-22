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

  it("envía calle al pasar de ESQUINA a NUMERO con dirección real", () => {
    const rowEsquina = {
      ...rowMonteagudo,
      numero_tipo: "ESQUINA",
      numero: "y maipu",
      esquina_key: "maipu",
      esquina_normalizada: "Maipú",
      calle: "San Juan",
      calle_normalizada: "San Juan",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBody(
      {
        ...EMPTY_COMPLETAR_FORM,
        calle: "Maipú",
        numero: "500",
        numero_tipo: "NUMERO",
        rubro_nombre: "Panadería",
      },
      { domicilioRow: rowEsquina, omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Maipú");
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("FromInline respeta calle editada aunque row tenga calle_normalizada distinta", () => {
    const rowEsquina = {
      ...rowMonteagudo,
      numero_tipo: "ESQUINA",
      calle: "San Juan",
      calle_normalizada: "San Juan",
      numero: "y Maipú",
      esquina_normalizada: "Maipú",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowEsquina,
      {
        calle: "Maipú",
        numero: "500",
        numero_tipo: "NUMERO",
        rubro_nombre: "Carnicería",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Maipú");
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("FromInline ESQUINA→NUMERO manda calle visible aunque merged ya traiga numero_tipo NUMERO", () => {
    const rowEsquina = {
      ruta_item_id: 9,
      numero_tipo: "ESQUINA",
      calle: "san juan",
      calle_key: "san juan",
      calle_normalizada: "San Juan",
      numero: "y mendoza",
      esquina_key: "mendoza",
      esquina_normalizada: "Mendoza",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowEsquina,
      {
        calle: "Mendoza",
        numero: "500",
        numero_tipo: "NUMERO",
        rubro_nombre: "Carnicería",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Mendoza");
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("FromInline ESQUINA→NUMERO sin calle en values hidrata calle de la fila para el payload", () => {
    const rowEsquina = {
      ruta_item_id: 10,
      numero_tipo: "ESQUINA",
      calle_normalizada: "San Juan",
      numero: "y mendoza",
      esquina_normalizada: "Mendoza",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowEsquina,
      {
        numero: "500",
        numero_tipo: "NUMERO",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("San Juan");
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("FromInline ESQUINA→NUMERO sin calle explícita ni hidratable no manda calle", () => {
    const rowEsquina = {
      ruta_item_id: 11,
      numero_tipo: "ESQUINA",
      numero: "y mendoza",
      esquina_normalizada: "Mendoza",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowEsquina,
      {
        calle: "",
        numero: "500",
        numero_tipo: "NUMERO",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("calle baseline + número editado cuando calle visible no cambió", () => {
    const body = buildCompletarTrabajoCierreBodyFromInline(
      rowMonteagudo,
      { calle: "Dr Bernardo Monteagudo", numero: "100", numero_tipo: "NUMERO" },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Dr Bernardo Monteagudo");
    expect(body.numero).toBe("100");
    expect(body.numero_tipo).toBe("NUMERO");
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

  it("REINSPECCION_NOTIFICACION sin edición domicilio no incluye domicilio en body", () => {
    const row = {
      ruta_item_id: 713,
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      calle: "San Martín",
      calle_normalizada: "San Martín",
      numero: "450",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        contraproducencia: "",
        acta_inspeccion_num: "000123",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBeUndefined();
    expect(body.numero_tipo).toBeUndefined();
    expect(body.rubro_nombre).toBeUndefined();
    expect(body.acta_inspeccion_num).toBe("000123");
  });

  it("REINSPECCION_OFICIO sin edición domicilio no incluye domicilio en body", () => {
    const row = {
      ruta_item_id: 714,
      tipo_iniciador: "REINSPECCION_OFICIO",
      calle: "Belgrano",
      calle_normalizada: "Belgrano",
      numero: "1200",
      numero_tipo: "NUMERO",
      rubro_nombre: "Carnicería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        tipo_actuacion: "VERIFICAR E INFORMAR",
        resultado_cumplimiento_oficio: "CUMPLE",
        acta_inspeccion_num: "000456",
      },
      { includeTipoActuacion: true }
    );
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBeUndefined();
    expect(body.rubro_nombre).toBeUndefined();
    expect(body.tipo_actuacion).toBe("VERIFICAR E INFORMAR");
    expect(body.resultado_cumplimiento_oficio).toBe("CUMPLE");
  });

  it("con edición calle/número incluye domicilio completo", () => {
    const row = {
      ruta_item_id: 715,
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      calle: "San Martín",
      calle_normalizada: "San Martín",
      numero: "450",
      numero_tipo: "NUMERO",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        calle: "Mendoza",
        numero: "500",
        numero_tipo: "NUMERO",
        acta_inspeccion_num: "000789",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Mendoza");
    expect(body.numero).toBe("500");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("calle baseline + número editado cuando solo cambia el número (PR11.2)", () => {
    const row = {
      ruta_item_id: 716,
      calle: "San Juan",
      calle_normalizada: "San Juan",
      numero: "100",
      numero_tipo: "NUMERO",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      { numero: "200", acta_inspeccion_num: "001" },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("San Juan");
    expect(body.numero).toBe("200");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("calle editada + número baseline cuando solo cambia la calle (PR11.2)", () => {
    const row = {
      ruta_item_id: 717,
      calle: "Maipú",
      calle_normalizada: "Maipú",
      numero: "34",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      { calle: "Mendoza", acta_inspeccion_num: "002" },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Mendoza");
    expect(body.numero).toBe("34");
    expect(body.numero_tipo).toBe("NUMERO");
  });

  it("rubro baseline se conserva al cambiar solo domicilio (PR11.2)", () => {
    const row = {
      ruta_item_id: 718,
      calle: "Maipú",
      calle_normalizada: "Maipú",
      numero: "34",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        calle: "Maipú",
        numero: "36",
        numero_tipo: "NUMERO",
        rubro_nombre: "Panadería",
        acta_inspeccion_num: "003",
      },
      { omitPrecargadoPr2: true }
    );
    expect(body.calle).toBe("Maipú");
    expect(body.numero).toBe("36");
    expect(body.rubro_nombre).toBe("Panadería");
  });

  it("rubro editado manda el nuevo valor (PR11.2)", () => {
    const row = {
      ruta_item_id: 719,
      calle: "Maipú",
      calle_normalizada: "Maipú",
      numero: "34",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      { rubro_nombre: "Carnicería", acta_inspeccion_num: "004" },
      { omitPrecargadoPr2: true }
    );
    expect(body.rubro_nombre).toBe("Carnicería");
    expect(body.calle).toBeUndefined();
    expect(body.numero).toBeUndefined();
  });

  it("verificar e informar con nueva inspección: solo número usa calle baseline (PR11.2)", () => {
    const row = {
      ruta_item_id: 720,
      tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
      calle: "Maipú",
      calle_normalizada: "Maipú",
      numero: "34",
      numero_tipo: "NUMERO",
      rubro_nombre: "Panadería",
    } as ICompletarTrabajoPendienteRow;
    const body = buildCompletarTrabajoCierreBodyFromInline(
      row,
      {
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: "si",
        calle: "Maipú",
        numero: "36",
        numero_tipo: "NUMERO",
        rubro_nombre: "Panadería",
        acta_inspeccion_num: "000042",
      },
      { includeTipoActuacion: true }
    );
    expect(body.calle).toBe("Maipú");
    expect(body.numero).toBe("36");
    expect(body.rubro_nombre).toBe("Panadería");
    expect(body.realizo_nueva_inspeccion).toBe(true);
  });
});

describe("buildCompletarTrabajoCierreBody verificar e informar", () => {
  it("envía realizo_nueva_inspeccion y omite actas cuando incluirInspeccionNormal es false", () => {
    const body = buildCompletarTrabajoCierreBody(
      {
        ...EMPTY_COMPLETAR_FORM,
        tipo_actuacion: "VERIFICAR E INFORMAR",
        realizo_nueva_inspeccion: "no",
        acta_inspeccion_num: "123456",
      },
      { incluirInspeccionNormal: false }
    );
    expect(body.realizo_nueva_inspeccion).toBe(false);
    expect(body.acta_inspeccion_num).toBeUndefined();
  });

  it("con nueva inspección sí envía actas", () => {
    const body = buildCompletarTrabajoCierreBody({
      ...EMPTY_COMPLETAR_FORM,
      realizo_nueva_inspeccion: "si",
      acta_inspeccion_num: "000042",
    });
    expect(body.realizo_nueva_inspeccion).toBe(true);
    expect(body.acta_inspeccion_num).toBe("000042");
  });
});
