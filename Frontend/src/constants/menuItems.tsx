import NoteAddIcon from '@mui/icons-material/NoteAdd';
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';
import ListAltIcon from '@mui/icons-material/ListAlt';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BadgeIcon from '@mui/icons-material/Badge';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import HomeIcon from '@mui/icons-material/Home';
import LocationOnIcon from "@mui/icons-material/LocationOn";
import RouteIcon from "@mui/icons-material/Route";
import type { JSX } from 'react';

// Definición de secciones del menú (agrupadas)
export interface MenuItem {
  text: string;
  icon: JSX.Element;
  path: string;
}

export interface MenuSection {
  label: string;
  items: MenuItem[];
}

// Secciones del menú lateral (estilo Spotify)
export const menuSections: MenuSection[] = [
  {
    label: "MAIN",
    items: [
      { text: "Inicio", icon: <HomeIcon />, path: "/inicio" },
    ],
  },
  {
    label: "CARGA",
    items: [
      { text: "Cargar Actuación", icon: <CreateNewFolderIcon />, path: "/cargarActuacion" },
      { text: "Cargar Relevamiento", icon: <NoteAddIcon />, path: "/cargarRelevamiento" },
      { text: "Cargar Personas", icon: <PersonAddIcon />, path: "/cargarPersonasCapacitadas" },
    ],
  },
  {
    label: "GESTIÓN",
    items: [
      { text: "Expedientes", icon: <DashboardIcon />, path: "/actuaciones" },
      { text: "Relevamientos", icon: <ListAltIcon />, path: "/relevamientos" },
      { text: "Ruta de trabajo", icon: <RouteIcon />, path: "/rutasTrabajo" },
      { text: "Gestionar domicilios", icon: <LocationOnIcon />, path: "/gestionarDomicilios" },
      { text: "Gestion Usuarios", icon: <BadgeIcon />, path: "/gestionDeUsuarios" },
      { text: "Dashboard", icon: <BarChartIcon />, path: "/dashboard" },
      { text: "Mapa", icon: <MapIcon />, path: "/mapa" },
    ],
  },
  {
    label: "CONFIGURACIÓN",
    items: [
      { text: "Sistema", icon: <SettingsIcon />, path: "/gestionSistema" },
    ],
  },
];

// Item de logout (separado, al final)
export const logoutItem: MenuItem = {
  text: "Cerrar Sesión",
  icon: <LogoutIcon />,
  path: "/login",
};

// Mapeo de rutas a labels para el breadcrumb
export const routeLabels: Record<string, string> = {
  "/inicio": "Inicio",
  "/cargarActuacion": "Carga de Actuaciones",
  "/cargarRelevamiento": "Carga de Relevamientos",
  "/cargarPersonasCapacitadas": "Carga de Personas Capacitadas",
  "/actuaciones": "Gestión de Expedientes",
  "/relevamientos": "Gestión de Relevamientos",
  "/rutasTrabajo": "Ruta de trabajo",
  "/gestionPersonasBpm": "Gestión Personas BPM",
  "/gestionDeUsuarios": "Gestión De Usuarios",
  "/dashboard": "Dashboard",
  "/gestionarDomicilios": "Gestionar domicilios",
  "/mapa": "Mapa",
  "/gestionSistema": "Configuración del Sistema",
  "/perfil": "Mi Perfil",
  "/pendientes": "Pendientes",
  "/pendientesVinculacionActa": "Pendientes Vinculación Acta",
  "/pendientesVinculacionOficio": "Pendientes Vinculación Oficio",
};

// Mantener compatibilidad con código existente (flat list)
export const menuItems = menuSections.flatMap(section => section.items);
