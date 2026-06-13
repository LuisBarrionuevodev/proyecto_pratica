import NoteAddIcon from "@mui/icons-material/NoteAdd";
import BarChartIcon from "@mui/icons-material/BarChart";
import DashboardIcon from "@mui/icons-material/Dashboard";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import ListAltIcon from "@mui/icons-material/ListAlt";
import BadgeIcon from "@mui/icons-material/Badge";
import LogoutIcon from "@mui/icons-material/Logout";
import HomeIcon from "@mui/icons-material/Home";
import RouteIcon from "@mui/icons-material/Route";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import StorefrontIcon from "@mui/icons-material/Storefront";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import HomeWorkIcon from "@mui/icons-material/HomeWork";
import type { JSX } from "react";

export interface MenuItem {
  text: string;
  icon: JSX.Element;
  path: string;
}

export interface MenuSection {
  label: string;
  items: MenuItem[];
}

/** UX-FILTROS-NAV-1: estructura operativa unificada (Configuración oculta en nav). */
export const menuSections: MenuSection[] = [
  {
    label: "MAIN",
    items: [{ text: "Inicio", icon: <HomeIcon />, path: "/inicio" }],
  },
  {
    label: "CARGA",
    items: [
      {
        text: "Cargar actuaciones",
        icon: <CreateNewFolderIcon />,
        path: "/cargarActuacion",
      },
      {
        text: "Cargar relevamientos y denuncias",
        icon: <NoteAddIcon />,
        path: "/cargarRelevamiento",
      },
    ],
  },
  {
    label: "OPERATIVA",
    items: [
      { text: "Ruta de trabajo", icon: <RouteIcon />, path: "/rutasTrabajo" },
      { text: "Completar trabajo", icon: <TaskAltIcon />, path: "/completarTrabajos" },
      {
        text: "Notificaciones gestión",
        icon: <NotificationsActiveIcon />,
        path: "/gestionNotificacion",
      },
      {
        text: "Comprobaciones gestión",
        icon: <FactCheckOutlinedIcon />,
        path: "/actasComprobacion",
      },
      {
        text: "Gestionar domicilios",
        icon: <HomeWorkIcon />,
        path: "/gestionarDomicilios",
      },
    ],
  },
  {
    label: "LISTAS",
    items: [
      { text: "Actuaciones", icon: <DashboardIcon />, path: "/actuaciones" },
      {
        text: "Relevamientos y denuncias",
        icon: <ListAltIcon />,
        path: "/relevamientos",
      },
      { text: "Establecimientos", icon: <StorefrontIcon />, path: "/establecimientos" },
    ],
  },
  {
    label: "INDICADORES Y MAPA",
    items: [
      { text: "Indicadores", icon: <BarChartIcon />, path: "/dashboard" },
      { text: "Mapa", icon: <MapIcon />, path: "/mapa" },
    ],
  },
  {
    label: "ADMINISTRACIÓN",
    items: [{ text: "Gestión de usuarios", icon: <BadgeIcon />, path: "/gestionDeUsuarios" }],
  },
];

export const logoutItem: MenuItem = {
  text: "Cerrar Sesión",
  icon: <LogoutIcon />,
  path: "/login",
};

export const routeLabels: Record<string, string> = {
  "/inicio": "Inicio",
  "/cargarActuacion": "Cargar actuaciones",
  "/cargarRelevamiento": "Cargar relevamientos y denuncias",
  "/cargarPersonasCapacitadas": "Gestión de capacitaciones",
  "/actuaciones": "Actuaciones",
  "/gestionNotificacion": "Notificaciones gestión",
  "/actasComprobacion": "Comprobaciones gestión",
  "/relevamientos": "Relevamientos y denuncias",
  "/establecimientos": "Establecimientos",
  "/rutasTrabajo": "Ruta de trabajo",
  "/completarTrabajos": "Completar trabajo",
  "/gestionPersonasBpm": "Gestión Personas BPM",
  "/gestionDeUsuarios": "Gestión de usuarios",
  "/dashboard": "Indicadores",
  "/gestionarDomicilios": "Gestionar domicilios",
  "/mapa": "Mapa",
  "/gestionSistema": "Configuración del sistema",
  "/perfil": "Mi Perfil",
  "/pendientes": "Pendientes",
  "/pendientesVinculacionActa": "Pendientes Vinculación Acta",
  "/pendientesVinculacionOficio": "Pendientes Vinculación Oficio",
};

export const menuItems = menuSections.flatMap((section) => section.items);
