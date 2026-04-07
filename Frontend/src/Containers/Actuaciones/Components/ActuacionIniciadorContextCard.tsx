import { Box, Typography } from "@mui/material";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function domicilioResumen(row: IActuacionListItem): string {
  const calle =
    row.calle_estado === "OK" && row.calle_normalizada
      ? row.calle_normalizada
      : row.calle ?? "";
  let numero = "";
  if (row.numero_tipo === "ESQUINA" && (row.numero_esquina || row.esquina_normalizada)) {
    numero = row.numero_esquina || row.esquina_normalizada || "";
  } else {
    numero = row.numero ?? "";
  }
  const line = [calle, numero].filter(Boolean).join(" ");
  return line.trim() || "—";
}

function inspectoresLinea(row: IActuacionListItem): string {
  const parts = [row.inspector1, row.inspector2, row.inspector3].filter((x) => x?.trim());
  return parts.length ? parts.join(", ") : "—";
}

type Props = {
  row: IActuacionListItem;
};

/**
 * Bloque superior de contexto (solo lectura), alineado al patrón de Completar trabajo.
 * Usa campos disponibles en el listado; tipo/prioridad/distrito de iniciador llegan cuando el API los exponga.
 */
export function ActuacionIniciadorContextCard({ row }: Props) {
  return (
    <Box
      sx={{
        p: 1.75,
        borderRadius: 2,
        bgcolor: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.12)",
        fontFamily: '"Tactic Sans", sans-serif',
      }}
    >
      <Typography
        variant="caption"
        sx={{ color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.06em" }}
      >
        Contexto operativo
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.82)", mt: 1, fontWeight: 600 }}>
        OT {dash(row.orden_trabajo_numero)}
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mt: 0.5 }}>
        Tipo de actuación: {dash(row.tipo_actuacion)}
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
        Contraproducencia: {dash(row.contraproducencia)}
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
        Rubro: {dash(row.rubro_nombre)}
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
        Fecha actuación: {dash(row.fecha_actuacion)}
      </Typography>
      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
          Domicilio
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)" }}>
          {domicilioResumen(row)}
        </Typography>
      </Box>
      <Box sx={{ mt: 1 }}>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", display: "block" }}>
          Inspectores
        </Typography>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)" }}>
          {inspectoresLinea(row)}
        </Typography>
      </Box>
      {row.nombre_local != null && String(row.nombre_local).trim() !== "" && (
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", mt: 0.5 }}>
          Nombre local: {dash(row.nombre_local)}
        </Typography>
      )}
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.4)", display: "block", mt: 1.25 }}>
        Prioridad, turno y distrito del iniciador se mostrarán aquí cuando el listado los incluya.
      </Typography>
    </Box>
  );
}
