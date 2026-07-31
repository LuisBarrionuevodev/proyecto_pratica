import { Box, Typography } from "@mui/material";

import { BandejaEllipsisCell } from "../../Actuaciones/Components/bandejaTableCells";
import type { IEstablecimientoOperativoListItem } from "../../../api/establecimientosOperativosApi";
import { establecimientoDomicilioLineaVisible } from "../utils/establecimientoDomicilioVisible";
import {
  establecimientoContribuyenteDocumentoLinea,
  establecimientoContribuyenteTitulo,
} from "../utils/establecimientoContribuyenteVisible";

/**
 * Celda unificada de domicilio normalizado con distrito opcional debajo.
 */
export function EstablecimientoListDomicilioCell({ row }: { row: IEstablecimientoOperativoListItem }) {
  const linea = establecimientoDomicilioLineaVisible(row);
  const distrito = (row.distrito_nombre ?? "").trim();
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.35, maxWidth: "100%" }}>
      <BandejaEllipsisCell value={linea} />
      {distrito ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>
          Distrito: {distrito}
        </Typography>
      ) : null}
    </Box>
  );
}

/**
 * Celda unificada contribuyente / razón social con documento debajo.
 */
export function EstablecimientoContribuyenteCell({ row }: { row: IEstablecimientoOperativoListItem }) {
  const titulo = establecimientoContribuyenteTitulo(row);
  const docLinea = establecimientoContribuyenteDocumentoLinea(row.documento);
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.35, maxWidth: "100%" }}>
      <BandejaEllipsisCell value={titulo} />
      {docLinea ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{docLinea}</Typography>
      ) : null}
    </Box>
  );
}
