import NoteAddIcon from '@mui/icons-material/NoteAdd';
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';
import ListAltIcon from '@mui/icons-material/ListAlt';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BadgeIcon from '@mui/icons-material/Badge';
import SettingsIcon from '@mui/icons-material/Settings';

export const menuItems = [
  { text: "Cargar Actuación", icon: <CreateNewFolderIcon/>, path: "/cargarActuacion" },
  { text: "Cargar Relevamiento", icon: <NoteAddIcon />, path: "/cargarRelevamiento" },
  { text: "Gestionar Expedientes", icon: <DashboardIcon />, path: "/actuaciones" },
  { text: "Gestión Relevamientos", icon: <ListAltIcon />, path: "/relevamientos" },
  { text: "Cargar Personas Capacitadas", icon: <PersonAddIcon />, path: "/cargarPersonasCapacitadas" },
  { text: "Gestión Personas BPM", icon: <BadgeIcon />, path: "/gestionPersonasBpm" },
  { text: "Dashboard", icon: <BarChartIcon />, path: "/dashboard" },
  { text: "Mapa", icon: <MapIcon />, path: "/mapa" },
  { text: "Gestión del Sistema", icon: <SettingsIcon />, path: "/gestionSistema" },
];
