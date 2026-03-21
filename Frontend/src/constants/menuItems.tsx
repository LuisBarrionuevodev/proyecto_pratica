import NoteAddIcon from "@mui/icons-material/NoteAdd";
import BarChartIcon from "@mui/icons-material/BarChart";
import DashboardIcon from "@mui/icons-material/Dashboard";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import ListAltIcon from "@mui/icons-material/ListAlt";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import BadgeIcon from "@mui/icons-material/Badge";
import SettingsIcon from "@mui/icons-material/Settings";
import LogoutIcon from "@mui/icons-material/Logout";
import HomeIcon from "@mui/icons-material/Home";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import RouteIcon from "@mui/icons-material/Route";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import StorefrontIcon from "@mui/icons-material/Storefront";
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

export const menuSections: MenuSection[] = [
  {
    label: "TRABAJO",
    items: [{ text: "Ruta de trabajo", icon: <RouteIcon />, path: "/rutasTrabajo" }],
  },
  {
    label: "MAIN",
    items: [{ text: "Inicio", icon: <HomeIcon />, path: "/inicio" }],
  },
  {
    label: "CARGA",
    items: [
      { text: "Cargar actas", icon: <CreateNewFolderIcon />, path: "/cargarActuacion" },
      { text: "Cargar relevamiento o denuncia", icon: <NoteAddIcon />, path: "/cargarRelevamiento" },
      { text: "Cargar Personas", icon: <PersonAddIcon />, path: "/cargarPersonasCapacitadas" },
    ],
  },
  {
    label: "GESTIÓN",
    items: [
      { text: "Actuaciones", icon: <DashboardIcon />, path: "/actuaciones" },
      { text: "Relevamientos", icon: <ListAltIcon />, path: "/relevamientos" },
      { text: "Establecimientos", icon: <StorefrontIcon />, path: "/establecimientos" },
      { text: "Completar trabajos", icon: <TaskAltIcon />, path: "/completarTrabajos" },
      { text: "Gestionar domicilios", icon: <LocationOnIcon />, path: "/gestionarDomicilios" },
      { text: "Gestión de usuarios", icon: <BadgeIcon />, path: "/gestionDeUsuarios" },
      { text: "Indicadores", icon: <BarChartIcon />, path: "/dashboard" },
      { text: "Mapa", icon: <MapIcon />, path: "/mapa" },
    ],
  },
  {
    label: "CONFIGURACIÓN",
    items: [{ text: "Sistema", icon: <SettingsIcon />, path: "/gestionSistema" }],
  },
];

export const logoutItem: MenuItem = {
  text: "Cerrar Sesión",
  icon: <LogoutIcon />,
  path: "/login",
};

export const routeLabels: Record<string, string> = {
  "/inicio": "Inicio",
  "/cargarActuacion": "Cargar actas",
  "/cargarRelevamiento": "Cargar relevamiento o denuncia",
  "/cargarPersonasCapacitadas": "Cargar Personas",
  "/actuaciones": "Actuaciones",
  "/relevamientos": "Relevamientos",
  "/establecimientos": "Establecimientos",
  "/rutasTrabajo": "Ruta de trabajo",
  "/completarTrabajos": "Completar trabajos",
  "/gestionPersonasBpm": "Gestión Personas BPM",
  "/gestionDeUsuarios": "Gestión de usuarios",
  "/dashboard": "Indicadores",
  "/gestionarDomicilios": "Gestionar domicilios",
  "/mapa": "Mapa",
  "/gestionSistema": "Sistema",
  "/perfil": "Mi Perfil",
  "/pendientes": "Pendientes",
  "/pendientesVinculacionActa": "Pendientes Vinculación Acta",
  "/pendientesVinculacionOficio": "Pendientes Vinculación Oficio",
};

export const menuItems = menuSections.flatMap((section) => section.items);
