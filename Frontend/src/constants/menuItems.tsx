import NoteAddIcon from '@mui/icons-material/NoteAdd';
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';

export const menuItems = [
  { text: "Cargar Actuación", icon: <CreateNewFolderIcon/>, path: "/cargarActuacion" },
  { text: "Cargar Relevamiento", icon: <NoteAddIcon />, path: "/cargarRelevamiento" },
  { text: "Gestionar Expedientes", icon: <DashboardIcon />, path: "/actuaciones" },
  { text: "Dashboard", icon: <BarChartIcon />, path: "/dashboard" },
  { text: "Mapa", icon: <MapIcon />, path: "/mapa" },
];
