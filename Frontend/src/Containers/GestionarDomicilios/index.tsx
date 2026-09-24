import { Navigate } from "react-router-dom";

/**
 * Compatibilidad PR6C.12/15: redirige a Mapa (geolocalización de domicilios).
 * La ruta principal en App.tsx también usa Navigate; este módulo queda por si algo lo importa.
 */
const GestionarDomicilios = () => {
  return <Navigate to="/mapa" replace />;
};

export default GestionarDomicilios;
