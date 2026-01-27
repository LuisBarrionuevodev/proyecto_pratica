import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import Login from "./Containers/Login";
import RecuperarCuenta from "./Containers/RecuperarCuenta";
import Inicio from "./Containers/Inicio";
import Actuaciones from "./Containers/Actuaciones";
import CargarRelevamientos from "./Containers/CargarRelevamientos";
import CargarActuaciones from "./Containers/CargarActuaciones";
import Dashboard from "./Containers/Dashboard";
import Relevamientos from "./Containers/Actuaciones/Containers/Relevamientos";
import Pendientes from "./Containers/Actuaciones/Containers/Pendientes";
import PendientesVinculacionActa from "./Containers/Actuaciones/Containers/PendientesVinculacionActa";
import PendientesVinculacionOficio from "./Containers/Actuaciones/Containers/PendientesVinculacionOficio";
import Mapa from "./Containers/Mapa";
import TopBar from "./Componets/TopBar";
import Perfil from "./Containers/Perfil";

// Componente wrapper que muestra TopBar solo en rutas permitidas
const AppLayout = () => {
  const location = useLocation();
  
  // Rutas donde NO se muestra el TopBar
  const hideTopBarRoutes = ["/", "/login", "/perfil"];
  const showTopBar = !hideTopBarRoutes.includes(location.pathname);

  return (
    <>
      {showTopBar && <TopBar />}
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/login" element={<Login />} />
        <Route path="/recuperarCuenta" element={<RecuperarCuenta />} />
        <Route path="/inicio" element={<Inicio />} />
        <Route path="/actuaciones" element={<Actuaciones />} />
        <Route path="/relevamientos" element={<Relevamientos />} />
        <Route path="/pendientes" element={<Pendientes />} />
        <Route path="/pendientesVinculacionActa" element={<PendientesVinculacionActa />} />
        <Route path="/pendientesVinculacionOficio" element={<PendientesVinculacionOficio />} />
        <Route path="/cargarRelevamiento" element={<CargarRelevamientos />} />
        <Route path="/cargarActuacion" element={<CargarActuaciones />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/mapa" element={<Mapa />} />
        <Route path="/perfil" element={<Perfil />} />
      </Routes>
    </>
  );
};

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App
