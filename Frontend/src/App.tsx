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
import { Box } from "@mui/material";
import NavLeft from "./Componets/NavLeft";
import { useState } from "react";

// Componente wrapper que muestra TopBar solo en rutas permitidas
const AppLayout = () => {
  const location = useLocation();

  // Rutas donde NO se muestra el TopBar
  const hideNavLeftRoutes = ["/", "/login", "inicio"];
  const showNavLeft = !hideNavLeftRoutes.includes(location.pathname);

  const [navOpen, setNavOpen] = useState(false);

  return (
    <>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: navOpen ? "240px 1fr" : "70px 1fr",
          gridTemplateRows: "90px 1fr",
          height: { lg: "98vh", xl: "94vh" },
          transition: "grid-template-columns 0.25s ease",
        }}
      >

          <Box>
            <NavLeft onToggle={setNavOpen} />
          </Box>


        {/* HEADER */}
        <Box sx={{ gridRow: "1 / 3", gridColumn: 1 }}>
          <TopBar />
        </Box>

        {/* MAIN (scroll acá) */}
        <Box
          sx={{
            gridRow: 2,
            overflowY: "auto",
            p: 0,
            width: { lg: "94%", xl: "96%" },
            border: "1px solid black",
            boxShadow: "0px 4px 8px black",
            borderRadius: "20px",
            ml: "50px",
          }}
        >
          <Routes>
            <Route path="/inicio" element={<Inicio />} />
            <Route path="/actuaciones" element={<Actuaciones />} />
            <Route path="/relevamientos" element={<Relevamientos />} />
            <Route path="/pendientes" element={<Pendientes />} />
            <Route
              path="/pendientesVinculacionActa"
              element={<PendientesVinculacionActa />}
            />
            <Route
              path="/pendientesVinculacionOficio"
              element={<PendientesVinculacionOficio />}
            />
            <Route
              path="/cargarRelevamiento"
              element={<CargarRelevamientos />}
            />
            <Route path="/cargarActuacion" element={<CargarActuaciones />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/mapa" element={<Mapa />} />
            <Route path="/perfil" element={<Perfil />} />
          </Routes>
        </Box>
      </Box>
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
