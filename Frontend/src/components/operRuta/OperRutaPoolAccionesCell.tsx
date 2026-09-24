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
  MENSAJE_EXITO_SACAR_DE_RUTA,
  OPER_RUTA_LABELS,
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

/** Acciones pool/ruta: gestionar en ruta, sacar de ruta o caption de ruta asignada. */
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
  const showSacar = puedeSacarDelPool(row) || puedeSacarDeRutaPool(row);
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
      onSuccess(MENSAJE_EXITO_SACAR_DE_RUTA);
      await onRefresh({ silent: true });
    } catch (err) {
      onError(parseApiError(err, "No se pudo sacar de ruta.").message);
    } finally {
      setBusy(false);
    }
  }, [row.pool_id, onRefresh, onSuccess, onError]);

  if (!showAgregar && !showSacar && !mostrarCaption) return null;

  return (
    <>
      <Stack spacing={0.5} alignItems="flex-start">
        {(showAgregar || showSacar) && (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {showAgregar && (
              <Tooltip title="Elegir fecha, turno, ruta y grupo">
                <span>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    disabled={busy}
                    onClick={() => setDialogOpen(true)}
                    data-testid="oper-ruta-agregar-ruta-trabajo"
                  >
                    {busy ? "…" : OPER_RUTA_LABELS.GESTIONAR_EN_RUTA}
                  </AppButton>
                </span>
              </Tooltip>
            )}
            {showSacar && (
              <Tooltip title="Quitar de la ruta operativa del día">
                <span>
                  <AppButton
                    dsVariant="danger"
                    dsSize="sm"
                    disabled={busy}
                    onClick={() => void handleLiberar()}
                    data-testid="oper-ruta-sacar-de-ruta"
                  >
                    {busy ? "…" : OPER_RUTA_LABELS.SACAR_DE_RUTA}
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
