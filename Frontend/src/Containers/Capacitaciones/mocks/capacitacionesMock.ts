import type { CapacitacionRow } from "../types/capacitaciones.types";

/** Dataset inicial alineado al mockup operativo (listado + participantes). */
export function getInitialCapacitacionesMock(): CapacitacionRow[] {
  return [
    {
      id: "cap-001",
      nombre: "Taller: Digitalización de Archivos v1",
      sede: "Sala A — Bromatología",
      fechaInicio: "2024-03-12",
      promotores: ["Lic. Ana Ríos", "Tec. Marcos Díaz"],
      participantes: [
        {
          id: "p1",
          nombre: "Julia",
          apellido: "Martínez",
          dni: "32.110.992",
          telefono: "381-555-0101",
          mail: "julia.m@mail.mock",
          lugarTrabajo: "Área Bromatología",
          examenAprobado: true,
          nota: "9",
        },
        {
          id: "p2",
          nombre: "Pedro",
          apellido: "Sánchez",
          dni: "28.441.001",
          telefono: "381-555-0102",
          mail: "pedro.s@mail.mock",
          lugarTrabajo: "Municipalidad",
          examenAprobado: false,
          nota: null,
        },
        {
          id: "p3",
          nombre: "Lucía",
          apellido: "Fernández",
          dni: "35.902.114",
          telefono: "",
          mail: "lucia.f@mail.mock",
          lugarTrabajo: "Inspección",
          examenAprobado: true,
          nota: "8",
        },
      ],
    },
    {
      id: "cap-002",
      nombre: "Introducción a Ley Orgánica Municipal",
      sede: "Auditorio Central",
      fechaInicio: "2024-03-05",
      promotores: ["Dr. Carlos Vega"],
      participantes: [
        {
          id: "p4",
          nombre: "Marta",
          apellido: "López",
          dni: "29.881.200",
          telefono: "381-555-0199",
          mail: "marta.l@mail.mock",
          lugarTrabajo: "Secretaría",
          examenAprobado: true,
          nota: "10",
        },
      ],
    },
    {
      id: "cap-003",
      nombre: "Buenas prácticas en inspección",
      sede: "Sala B",
      fechaInicio: "2024-02-20",
      promotores: ["Cap. Luis Gómez", "Tec. Paula Ruiz", "Lic. Diego Mena"],
      participantes: [],
    },
    {
      id: "cap-004",
      nombre: "Uso del sistema DIGITALIZA",
      sede: "Laboratorio 2",
      fechaInicio: "2024-01-15",
      promotores: ["Soporte técnico", "Coord. Sistemas"],
      participantes: [
        {
          id: "p5",
          nombre: "Roberto",
          apellido: "Paz",
          dni: "31.002.881",
          telefono: "",
          mail: "",
          lugarTrabajo: "IT",
          examenAprobado: false,
          nota: null,
        },
      ],
    },
  ];
}
