/** @jsxImportSource react */

import {
  BandejaEllipsisCell,
  BandejaSegmentChipsCell,
  splitCommaList,
} from "../../Actuaciones/Components/bandejaTableCells";

export type HistorialInspectoresCellProps = {
  inspectoresTexto?: string | null;
};

/**
 * Columna Inspectores del historial de Establecimientos (misma regla que Actuaciones).
 */
export function HistorialInspectoresCell({ inspectoresTexto }: HistorialInspectoresCellProps) {
  const texto = inspectoresTexto?.trim();
  if (!texto) {
    return <BandejaEllipsisCell value="—" />;
  }
  const segments = splitCommaList(texto);
  if (segments.length <= 1) {
    return <BandejaEllipsisCell value={texto} />;
  }
  return <BandejaSegmentChipsCell segments={segments} />;
}
