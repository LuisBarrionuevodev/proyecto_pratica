import type { ComponentType } from "react";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ListAltIcon from "@mui/icons-material/ListAlt";
import BadgeIcon from "@mui/icons-material/Badge";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import RouteIcon from "@mui/icons-material/Route";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import HomeWorkIcon from "@mui/icons-material/HomeWork";
import StorefrontIcon from "@mui/icons-material/Storefront";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";

export type InicioAccesoItem = {
  to: string;
  Icon: ComponentType<{ sx?: object }>;
  title: string;
  description: string;
};

/** UX-FILTROS-NAV-1: accesos alineados al menú lateral (sin Configuración). */
export const INICIO_ACCESOS: InicioAccesoItem[] = [
  {
    to: "/cargarActuacion",
    Icon: CreateNewFolderIcon,
    title: "Cargar actuaciones",
    description: "Alta de actas y actuaciones del día",
  },
  {
    to: "/cargarRelevamiento",
    Icon: NoteAddIcon,
    title: "Cargar relevamientos y denuncias",
    description: "Relevamientos de campo y denuncias",
  },
  {
    to: "/rutasTrabajo",
    Icon: RouteIcon,
    title: "Ruta de trabajo",
    description: "Planificar y publicar rutas",
  },
  {
    to: "/completarTrabajos",
    Icon: TaskAltIcon,
    title: "Completar trabajo",
    description: "Cierre de visitas del día",
  },
  {
    to: "/gestionNotificacion",
    Icon: NotificationsActiveIcon,
    title: "Notificaciones gestión",
    description: "Plazos, vencimientos e historial",
  },
  {
    to: "/actasComprobacion",
    Icon: FactCheckOutlinedIcon,
    title: "Comprobaciones gestión",
    description: "Expedientes, oficios y recorrido",
  },
  {
    to: "/gestionarDomicilios",
    Icon: HomeWorkIcon,
    title: "Gestionar domicilios",
    description: "Nomenclatura y geolocalización de domicilios",
  },
  {
    to: "/actuaciones",
    Icon: DashboardIcon,
    title: "Actuaciones",
    description: "Consulta y edición de actuaciones",
  },
  {
    to: "/relevamientos",
    Icon: ListAltIcon,
    title: "Relevamientos y denuncias",
    description: "Bandejas pendientes y realizados",
  },
  {
    to: "/establecimientos",
    Icon: StorefrontIcon,
    title: "Establecimientos",
    description: "Fichas operativas por domicilio",
  },
  {
    to: "/dashboard",
    Icon: BarChartIcon,
    title: "Indicadores",
    description: "Panel de indicadores",
  },
  {
    to: "/mapa",
    Icon: MapIcon,
    title: "Mapa",
    description: "Vista territorial operativa",
  },
  {
    to: "/gestionDeUsuarios",
    Icon: BadgeIcon,
    title: "Gestión de usuarios",
    description: "Alta, edición y estado de usuarios",
  },
];
