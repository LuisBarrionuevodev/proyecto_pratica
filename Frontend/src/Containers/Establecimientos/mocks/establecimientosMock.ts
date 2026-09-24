import type {
  IEstablecimientoDetalle,
  IEstablecimientoListRow,
} from "../types/establecimientos.types";

const BASE: IEstablecimientoDetalle[] = [
  {
    id: "est-001",
    calle: "Av. San Martín 1240",
    interseccion: "Esq. Belgrano",
    rubro: "GASTRONOMÍA",
    rubroSlug: "gastronomia",
    nombre: "Laura",
    apellido: "Fernández",
    dni: "28.441.092",
    distrito: "Centro",
    fechaUltimaInspeccion: "2024-05-14",
    razonSocial: "CAFÉ DEL PLAZA",
    rubroDetalle: "SERVICIO DE GASTRONOMÍA Y BEBIDAS",
    estadoAdmin: "HABILITADO",
    direccionCompleta: "Av. San Martín 1240 esq. Belgrano, Centro",
    historialInspecciones: [
      {
        id: "h1",
        fecha: "2024-05-14 09:15",
        tipoInspeccion: "Relevamiento de Salubridad",
        ordenTrabajo: "#OT-2024-8841",
        inspectoresIniciales: "JR, ML",
        resultado: "CONFORME",
      },
      {
        id: "h2",
        fecha: "2024-03-02 11:40",
        tipoInspeccion: "Inspección ordinaria",
        ordenTrabajo: "#OT-2024-1202",
        inspectoresIniciales: "PG",
        resultado: "OBSERVADO",
      },
    ],
    actuaciones: [
      {
        id: "a1",
        fecha: "2024-05-14",
        tipo: "Inspección",
        resumen: "Sin observaciones críticas.",
      },
    ],
    documentosMock: [
      { nombre: "Habilitación_sanitaria.pdf", tipo: "pdf" },
      { nombre: "Plano_local.jpg", tipo: "img" },
    ],
    alertaTitulo: null,
    alertaSubtitulo: null,
  },
  {
    id: "est-002",
    calle: "Av. Libertador 4402",
    interseccion: "Cnel. Díaz",
    rubro: "MINORISTA",
    rubroSlug: "minorista",
    nombre: "Alejandro G.",
    apellido: "Domínguez",
    dni: "24.588.192",
    distrito: "Norte",
    fechaUltimaInspeccion: "2024-05-14",
    razonSocial: "SUPERMERCADO LOS ALPES - SUC. NORTE",
    rubroDetalle: "VENTA MINORISTA DE PRODUCTOS ALIMENTICIOS",
    estadoAdmin: "HABILITADO",
    direccionCompleta: "Av. Libertador 4402 y Cnel. Díaz, Norte",
    historialInspecciones: [
      {
        id: "h1",
        fecha: "2024-05-14 09:15",
        tipoInspeccion: "Relevamiento de Salubridad",
        ordenTrabajo: "#OT-2024-8841",
        inspectoresIniciales: "JR, ML",
        resultado: "CONFORME",
      },
      {
        id: "h2",
        fecha: "2024-04-01 14:20",
        tipoInspeccion: "Control documentación",
        ordenTrabajo: "#OT-2024-7100",
        inspectoresIniciales: "AS",
        resultado: "APROBADO",
      },
      {
        id: "h3",
        fecha: "2024-02-18 10:05",
        tipoInspeccion: "Inspección integral",
        ordenTrabajo: "#OT-2024-5012",
        inspectoresIniciales: "JR, CR",
        resultado: "INFRACCION",
      },
      {
        id: "h4",
        fecha: "2023-11-22 16:30",
        tipoInspeccion: "Seguimiento",
        ordenTrabajo: "#OT-2023-9901",
        inspectoresIniciales: "ML",
        resultado: "OBSERVADO",
      },
    ],
    actuaciones: [
      {
        id: "a1",
        fecha: "2024-05-14",
        tipo: "Inspección",
        resumen: "Condiciones generales conformes.",
      },
      {
        id: "a2",
        fecha: "2024-02-18",
        tipo: "Acta",
        resumen: "Observaciones menores registradas.",
      },
    ],
    documentosMock: [
      { nombre: "Plano_Aprobado.pdf", tipo: "pdf" },
      { nombre: "Licencia_2023.pdf", tipo: "pdf" },
    ],
    alertaTitulo: "Renovación de Licencia",
    alertaSubtitulo: "VENCIMIENTO EN 12 DÍAS",
  },
  {
    id: "est-003",
    calle: "Rivadavia 2100",
    interseccion: "—",
    rubro: "INDUSTRIAL",
    rubroSlug: "industrial",
    nombre: "Martín",
    apellido: "Costa",
    dni: "31.002.881",
    distrito: "Sur",
    fechaUltimaInspeccion: "2024-01-10",
    razonSocial: "ELABORADOS SUR S.A.",
    rubroDetalle: "ELABORACIÓN DE PRODUCTOS ALIMENTICIOS",
    estadoAdmin: "PENDIENTE",
    direccionCompleta: "Rivadavia 2100, Sur",
    historialInspecciones: [
      {
        id: "h1",
        fecha: "2024-01-10 08:45",
        tipoInspeccion: "Inspección inicial",
        ordenTrabajo: "#OT-2024-0105",
        inspectoresIniciales: "PG, ML",
        resultado: "OBSERVADO",
      },
    ],
    actuaciones: [],
    documentosMock: [{ nombre: "Solicitud_trámite.pdf", tipo: "pdf" }],
    alertaTitulo: null,
    alertaSubtitulo: null,
  },
  {
    id: "est-004",
    calle: "Mitre 890",
    interseccion: "San Lorenzo",
    rubro: "SERVICIOS",
    rubroSlug: "servicios",
    nombre: "Patricia",
    apellido: "Vega",
    dni: "27.110.334",
    distrito: "Centro",
    fechaUltimaInspeccion: "2023-12-05",
    razonSocial: "LAVADERO MITRE",
    rubroDetalle: "SERVICIOS DE LIMPIEZA TEXTIL",
    estadoAdmin: "HABILITADO",
    direccionCompleta: "Mitre 890 esq. San Lorenzo, Centro",
    historialInspecciones: [
      {
        id: "h1",
        fecha: "2023-12-05 12:00",
        tipoInspeccion: "Verificación",
        ordenTrabajo: "#OT-2023-8800",
        inspectoresIniciales: "CR",
        resultado: "CONFORME",
      },
    ],
    actuaciones: [
      {
        id: "a1",
        fecha: "2023-12-05",
        tipo: "Comprobación",
        resumen: "Documentación al día.",
      },
    ],
    documentosMock: [],
    alertaTitulo: null,
    alertaSubtitulo: null,
  },
  {
    id: "est-005",
    calle: "Sarmiento 450",
    interseccion: "—",
    rubro: "MINORISTA",
    rubroSlug: "minorista",
    nombre: "Diego",
    apellido: "Ríos",
    dni: "33.992.100",
    distrito: "Oeste",
    fechaUltimaInspeccion: "2023-08-01",
    razonSocial: "KIOSCO SARMIENTO",
    rubroDetalle: "COMERCIO MINORISTA NO ESPECIALIZADO",
    estadoAdmin: "INHABILITADO",
    direccionCompleta: "Sarmiento 450, Oeste",
    historialInspecciones: [],
    actuaciones: [],
    documentosMock: [],
    alertaTitulo: null,
    alertaSubtitulo: null,
  },
];

export function getMockEstablecimientosDetalle(): IEstablecimientoDetalle[] {
  return BASE.map((b) => ({ ...b }));
}

function toListRow(d: IEstablecimientoDetalle): IEstablecimientoListRow {
  return {
    id: d.id,
    calle: d.calle,
    interseccion: d.interseccion,
    rubro: d.rubro,
    rubroSlug: d.rubroSlug,
    nombre: d.nombre,
    apellido: d.apellido,
    dni: d.dni,
    distrito: d.distrito,
    fechaUltimaInspeccion: d.fechaUltimaInspeccion,
    razonSocial: d.razonSocial,
    rubroDetalle: d.rubroDetalle,
    estadoAdmin: d.estadoAdmin,
    direccionCompleta: d.direccionCompleta,
  };
}

export function getMockEstablecimientosList(): IEstablecimientoListRow[] {
  return BASE.map(toListRow);
}

export function getMockEstablecimientoById(id: string): IEstablecimientoDetalle | undefined {
  return BASE.find((e) => e.id === id);
}
