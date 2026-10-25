import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AppSessionProvider } from "./auth/AppSessionProvider";
import Login from "./Containers/Login";
import RecuperarCuenta from "./Containers/RecuperarCuenta";
import Inicio from "./Containers/Inicio";
import AcercaDe from "./Containers/AcercaDe";
import Actuaciones from "./Containers/Actuaciones";
import CompletarTrabajos from "./Containers/CompletarTrabajos";
import AppLayout from "./layouts/AppLayout";
import {
  LazyActasComprobacionPage,
  LazyCargarActuaciones,
  LazyCargarRelevamientos,
  LazyDashboard,
  LazyEstablecimientoDetallePage,
  LazyEstablecimientosLayout,
  LazyEstablecimientosListPage,
  LazyGestionCapacitacionesPage,
  LazyGestionDeUsuarios,
  LazyGestionNotificacionPage,
  LazyGestionSistemaPage,
  LazyHistorialContribuyentePage,
  LazyMapa,
  LazyPendientes,
  LazyPendientesVinculacionActa,
  LazyPendientesVinculacionOficio,
  LazyPerfil,
  LazyRelevamientos,
  LazyRutasTrabajo,
} from "./routing/lazyRouteModules";

/**
 * App - Enrutador principal (React Router v6)
 *
 * Estructura de rutas:
 * - Rutas públicas (sin layout): /login, /recuperarCuenta, /inicio
 * - Rutas privadas (con AppLayout): lazy vía Suspense en AppLayout (PERF.4)
 *
 * Eager: login, inicio, Mis trabajos (`/actuaciones`), Completar trabajo.
 */
function App() {
  return (
    <Router>
      <AppSessionProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/login" />} />
          <Route path="/login" element={<Login />} />
          <Route path="/recuperarCuenta" element={<RecuperarCuenta />} />
          <Route path="/inicio" element={<Inicio />} />
          <Route path="/acerca-de" element={<AcercaDe />} />

          <Route element={<AppLayout />}>
            <Route path="/gestionDeUsuarios" element={<LazyGestionDeUsuarios />} />
            <Route path="/actuaciones" element={<Actuaciones />} />
            <Route path="/gestionNotificacion" element={<LazyGestionNotificacionPage />} />
            <Route path="/actasComprobacion" element={<LazyActasComprobacionPage />} />
            <Route path="/relevamientos" element={<LazyRelevamientos />} />
            <Route path="/pendientes" element={<LazyPendientes />} />
            <Route path="/pendientesVinculacionActa" element={<LazyPendientesVinculacionActa />} />
            <Route path="/pendientesVinculacionOficio" element={<LazyPendientesVinculacionOficio />} />
            <Route path="/cargarRelevamiento" element={<LazyCargarRelevamientos />} />
            <Route path="/cargarActuacion" element={<LazyCargarActuaciones />} />
            <Route path="/dashboard" element={<LazyDashboard />} />
            <Route path="/gestionarDomicilios" element={<Navigate to="/mapa" replace />} />
            <Route path="/rutasTrabajo" element={<LazyRutasTrabajo />} />
            <Route path="/completarTrabajos" element={<CompletarTrabajos />} />
            <Route path="/mapa" element={<LazyMapa />} />
            <Route path="/perfil" element={<LazyPerfil />} />
            <Route path="/cargarPersonasCapacitadas" element={<LazyGestionCapacitacionesPage />} />
            <Route path="/gestionSistema" element={<LazyGestionSistemaPage />} />
            <Route path="/establecimientos" element={<LazyEstablecimientosLayout />}>
              <Route index element={<LazyEstablecimientosListPage />} />
              <Route path="historial-contribuyente" element={<LazyHistorialContribuyentePage />} />
              <Route path=":id" element={<LazyEstablecimientoDetallePage />} />
            </Route>
          </Route>
        </Routes>
      </AppSessionProvider>
    </Router>
  );
}

export default App;
