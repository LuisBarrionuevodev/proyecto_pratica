import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Login from "./Containers/Login";
import RecuperarCuenta from "./Containers/RecuperarCuenta";
import Inicio from "./Containers/Inicio";
import Actuaciones from "./Containers/Actuaciones";
import CargarRelevamientos from "./Containers/CargarRelevamientos";
import CargarActuaciones from "./Containers/CargarActuaciones";
import Dashboard from "./Containers/Dashboard";
import Relevamientos from "./Containers/Relevamientos";
import Pendientes from "./Containers/Actuaciones/Containers/Pendientes";
import PendientesVinculacionActa from "./Containers/Actuaciones/Containers/PendientesVinculacionActa";
import PendientesVinculacionOficio from "./Containers/Actuaciones/Containers/PendientesVinculacionOficio";
import Mapa from "./Containers/Mapa";
import GestionarDomicilios from "./Containers/GestionarDomicilios";
import Perfil from "./Containers/Perfil";
import AppLayout from "./layouts/AppLayout";
import GestionDeUsuarios from "./Containers/GestionDeUsuarios";
import RutasTrabajo from "./Containers/RutasTrabajo";
import CompletarTrabajos from "./Containers/CompletarTrabajos";
import PlaceholderModule from "./Containers/PlaceholderModule";

/**
 * App - Enrutador principal (React Router v6)
 * 
 * Estructura de rutas:
 * - Rutas públicas (sin layout): /login, /recuperarCuenta, /inicio
 * - Rutas privadas (con AppLayout): todas las demás
 * 
 * El AppLayout incluye NavLeft + TopBar + ContentShell con scroll.
 * Al navegar entre rutas privadas, solo cambia el contenido del Outlet.
 */
function App() {
  return (
    <Router>
      <Routes>
        {/* Rutas públicas - SIN layout (sin NavLeft ni TopBar) */}
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/login" element={<Login />} />
        <Route path="/recuperarCuenta" element={<RecuperarCuenta />} />
        <Route path="/inicio" element={<Inicio />} />

        {/* Rutas privadas - CON AppLayout (NavLeft + TopBar + ContentShell) */}
        <Route element={<AppLayout />}>
          <Route path="/gestionDeUsuarios" element={<GestionDeUsuarios/>}/>
          <Route path="/actuaciones" element={<Actuaciones />} />
          <Route path="/relevamientos" element={<Relevamientos />} />
          <Route path="/pendientes" element={<Pendientes />} />
          <Route path="/pendientesVinculacionActa" element={<PendientesVinculacionActa />} />
          <Route path="/pendientesVinculacionOficio" element={<PendientesVinculacionOficio />} />
          <Route path="/cargarRelevamiento" element={<CargarRelevamientos />} />
          <Route path="/cargarActuacion" element={<CargarActuaciones />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/gestionarDomicilios" element={<GestionarDomicilios />} />
          <Route path="/rutasTrabajo" element={<RutasTrabajo />} />
          <Route path="/completarTrabajos" element={<CompletarTrabajos />} />
          <Route path="/mapa" element={<Mapa />} />
          <Route path="/perfil" element={<Perfil />} />
          <Route path="/cargarPersonasCapacitadas" element={<PlaceholderModule titulo="Cargar Personas" />} />
          <Route path="/gestionSistema" element={<PlaceholderModule titulo="Sistema" />} />
          <Route path="/establecimientos" element={<PlaceholderModule titulo="Establecimientos" />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
