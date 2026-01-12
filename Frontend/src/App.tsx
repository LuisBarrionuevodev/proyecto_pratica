import { BrowserRouter as Router, Routes, Route, Navigate, } from "react-router-dom";
import Login from "./Containers/Login";
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

function App() {


  return (

    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/login" element={ <Login/> } />
        <Route path="/inicio" element={ <Inicio/> } />
        <Route path="/actuaciones" element={ <Actuaciones/> } />
        <Route path="/relevamientos" element={ <Relevamientos/> } />
        <Route path="/pendientes" element={ <Pendientes/> } />
        <Route path="/pendientesVinculacionActa" element={ <PendientesVinculacionActa/> } />
        <Route path="/pendientesVinculacionOficio" element={ <PendientesVinculacionOficio/> } />
        <Route path="/cargarRelevamiento" element={ <CargarRelevamientos/> } />
        <Route path="/cargarActuacion" element={ <CargarActuaciones/> } />
        <Route path="/dashboard" element={ <Dashboard/> } />
        <Route path="/mapa" element={ <Mapa/> } />
      </Routes>
    </Router>

  )
}

export default App
