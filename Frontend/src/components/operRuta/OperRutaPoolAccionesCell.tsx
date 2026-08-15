import { useCallback, useState } from "react";
import { Stack, Tooltip, Typography } from "@mui/material";

import { liberarRutaPoolDia } from "../../api/rutaPoolDiaApi";
import { AppButton } from "../../ui";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { parseApiError } from "../../utils/parseApiError";
import {
  puedeAgregarARutaDeTrabajo,
  puedeSacarDelPool,
  puedeSacarDeRutaPool,
  debeMostrarGestionarDesdeRutaTrabajo,
  MENSAJE_GESTIONAR_DESDE_RUTA_TRABAJO,
  type OperRutaPoolFila,
  type OperRutaRefreshOptions,
} from "../../utils/operRutaPoolAcciones";
import { AgregarARutaOperDialog } from "./AgregarARutaOperDialog";

export type OperRutaPoolAccionesCellProps = {
  row: OperRutaPoolFila;
  fechaOperativa?: string;
  onRefresh: (opts?: OperRutaRefreshOptions) => void | Promise<void>;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
};

/** Acciones pool/ruta: agregar, sacar del pool o liberar de ruta borrador. */
export function OperRutaPoolAccionesCell({
  row,
  fechaOperativa,
  onRefresh,
  onSuccess,
  onError,
}: OperRutaPoolAccionesCellProps) {
  const fecha = fechaOperativa ?? fechaLocalHoyIso();
  const iniciadorId = row.iniciador_id != null ? Number(row.iniciador_id) : null;
  const [dialogOpen, setDialogOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const showAgregar = puedeAgregarARutaDeTrabajo(row);
  const showSacarPool = puedeSacarDelPool(row);
  const showSacarRuta = puedeSacarDeRutaPool(row);
  const mostrarCaption = debeMostrarGestionarDesdeRutaTrabajo(row);

  const handleDialogSuccess = useCallback(
    async (message: string) => {
      onSuccess(message);
      await onRefresh({ silent: true });
    },
    [onRefresh, onSuccess]
  );

  const handleLiberar = useCallback(async () => {
    const poolId = row.pool_id != null ? Number(row.pool_id) : null;
    if (poolId == null) {
      onError("No se encontró el ítem en el pool del día.");
      return;
    }
    setBusy(true);
    try {
      await liberarRutaPoolDia(poolId);
      onSuccess(showSacarRuta ? "Sacado de ruta/pool." : "Sacado del pool del día.");
      await onRefresh({ silent: true });
    } catch (err) {
      onError(parseApiError(err, "No se pudo liberar el pendiente del pool/ruta.").message);
    } finally {
      setBusy(false);
    }
  }, [row.pool_id, onRefresh, onSuccess, onError, showSacarRuta]);

  if (!showAgregar && !showSacarPool && !showSacarRuta && !mostrarCaption) return null;

  return (
    <>
      <Stack spacing={0.5} alignItems="flex-start">
        {(showAgregar || showSacarPool || showSacarRuta) && (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {showAgregar && (
              <Tooltip title="Elegir fecha, turno, ruta y pool o grupo">
                <span>
                  <AppButton
                    dsVariant="secondary"
                    dsSize="sm"
                    disabled={busy}
                    onClick={() => setDialogOpen(true)}
                    data-testid="oper-ruta-agregar-ruta-trabajo"
                  >
                    {busy ? "…" : "Agregar a ruta de trabajo"}
                  </AppButton>
                </span>
              </Tooltip>
            )}
            {showSacarPool && (
              <Tooltip title="Quitar del pool operativo del día">
                <span>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    disabled={busy}
                    onClick={() => void handleLiberar()}
                    data-testid="oper-ruta-sacar-pool"
                  >
                    {busy ? "…" : "Sacar del pool"}
                  </AppButton>
                </span>
              </Tooltip>
            )}
            {showSacarRuta && (
              <Tooltip title="Quitar de ruta borrador y pool (sin OT)">
                <span>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    disabled={busy}
                    onClick={() => void handleLiberar()}
                    data-testid="oper-ruta-sacar-ruta-pool"
                  >
                    Sacar de ruta/pool
                  </AppButton>
                </span>
              </Tooltip>
            )}
          </Stack>
        )}
        {mostrarCaption ? (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ lineHeight: 1.35, maxWidth: 220 }}
            data-testid="oper-ruta-gestionar-desde-ruta"
          >
            {MENSAJE_GESTIONAR_DESDE_RUTA_TRABAJO}
          </Typography>
        ) : null}
      </Stack>
      <AgregarARutaOperDialog
        open={dialogOpen}
        iniciadorId={iniciadorId}
        estadoOperativoPool={row.estado_operativo_pool}
        operContext={row}
        fechaOperativa={fecha}
        onClose={() => setDialogOpen(false)}
        onSuccess={handleDialogSuccess}
        onError={onError}
      />
    </>
  );
}
