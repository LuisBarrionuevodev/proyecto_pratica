import type { ComponentType } from "react";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ListAltIcon from "@mui/icons-material/ListAlt";
import BadgeIcon from "@mui/icons-material/Badge";
import SettingsSuggestIcon from "@mui/icons-material/SettingsSuggest";

export type InicioAccesoItem = {
  to: string;
  Icon: ComponentType<{ sx?: object }>;
  title: string;
  description: string;
};

/** Orden: fila 1 (2 izq), fila 2 (2 izq), fila 3 (2 izq) — coincide con grilla 3×3 desktop. */
export const INICIO_ACCESOS: InicioAccesoItem[] = [
  {
    to: "/cargarPersonasCapacitadas",
    Icon: PersonAddIcon,
    title: "Cargar Personas",
    description: "Personas capacitadas para inspecciones",
  },
  {
    to: "/cargarRelevamiento",
    Icon: NoteAddIcon,
    title: "Cargar relevamiento o denuncia",
    description: "Relevamientos y denuncias",
  },
  {
    to: "/actuaciones",
    Icon: DashboardIcon,
    title: "Actuaciones",
    description: "Gestión de actuaciones y expedientes",
  },
  {
    to: "/relevamientos",
    Icon: ListAltIcon,
    title: "Relevamientos",
    description: "Visualiza, edita y elimina relevamientos",
  },
  {
    to: "/gestionDeUsuarios",
    Icon: BadgeIcon,
    title: "Gestión de usuarios",
    description: "Gestiona usuarios existentes",
  },
  {
    to: "/gestionSistema",
    Icon: SettingsSuggestIcon,
    title: "Sistema",
    description: "Configuración y administración del sistema",
  },
];
