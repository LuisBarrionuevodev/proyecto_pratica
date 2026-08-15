import { useCallback, useState } from "react";
import { Stack, Tooltip } from "@mui/material";

import { createRutaPoolDia, listRutaPoolDia } from "../../api/rutaPoolDiaApi";
import { AppButton } from "../../ui";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { parseApiError } from "../../utils/parseApiError";
import {
  puedeAgregarAlPool,
  puedeAgregarARuta,
  type OperRutaPoolFila,
} from "../../utils/operRutaPoolAcciones";
import { AgregarARutaOperDialog } from "./AgregarARutaOperDialog";

export type OperRutaPoolAccionesCellProps = {
  row: OperRutaPoolFila;
  fechaOperativa?: string;
  onRefresh: () => void | Promise<void>;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
};

async function resolverPoolIdEnPool(iniciadorId: number, fecha: string): Promise<number | null> {
  const resp = await listRutaPoolDia({ fecha, estado: "EN_POOL", per_page: 100 });
  const match = (resp.items ?? []).find(
    (item) => Number(item.iniciador_id ?? item.iniciador_ruta_id) === iniciadorId
  );
  return match?.pool_id ?? null;
}

/** Acciones OPER-RUTA.5: agregar al pool / agregar a ruta borrador. */
export function OperRutaPoolAccionesCell({
  row,
  fechaOperativa,
  onRefresh,
  onSuccess,
  onError,
}: OperRutaPoolAccionesCellProps) {
  const fecha = fechaOperativa ?? fechaLocalHoyIso();
  const iniciadorId = row.iniciador_id != null ? Number(row.iniciador_id) : null;
  const [busy, setBusy] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingPoolId, setPendingPoolId] = useState<number | null>(null);

  const showPool = puedeAgregarAlPool(row);
  const showRuta = puedeAgregarARuta(row);

  const handleAgregarAlPool = useCallback(async () => {
    if (iniciadorId == null) return;
    setBusy(true);
    try {
      await createRutaPoolDia({
        origen_tipo: "INICIADOR",
        iniciador_ruta_id: iniciadorId,
        fecha,
      });
      onSuccess("Agregado al pool del día.");
      await onRefresh();
    } catch (err) {
      onError(parseApiError(err, "No se pudo agregar al pool del día.").message);
    } finally {
      setBusy(false);
    }
  }, [iniciadorId, fecha, onRefresh, onSuccess, onError]);

  const handleAgregarARuta = useCallback(async () => {
    if (iniciadorId == null) return;
    setBusy(true);
    try {
      let poolId = await resolverPoolIdEnPool(iniciadorId, fecha);
      if (poolId == null && puedeAgregarAlPool(row)) {
        const created = await createRutaPoolDia({
          origen_tipo: "INICIADOR",
          iniciador_ruta_id: iniciadorId,
          fecha,
        });
        poolId = created.item.pool_id;
      }
      if (poolId == null) {
        onError("No se encontró el ítem en el pool del día.");
        return;
      }
      setPendingPoolId(poolId);
      setDialogOpen(true);
    } catch (err) {
      onError(parseApiError(err, "No se pudo preparar la asignación a ruta.").message);
    } finally {
      setBusy(false);
    }
  }, [iniciadorId, fecha, row, onError]);

  const handleDialogSuccess = useCallback(async () => {
    onSuccess("Agregado a la ruta borrador.");
    await onRefresh();
  }, [onRefresh, onSuccess]);

  if (!showPool && !showRuta) return null;

  return (
    <>
      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
        {showPool && (
          <Tooltip title="Incorporar al pool operativo del día">
            <span>
              <AppButton
                dsVariant="secondary"
                dsSize="sm"
                disabled={busy}
                onClick={() => void handleAgregarAlPool()}
                data-testid="oper-ruta-agregar-pool"
              >
                Agregar al pool
              </AppButton>
            </span>
          </Tooltip>
        )}
        {showRuta && (
          <Tooltip title="Asignar a una ruta borrador existente">
            <span>
              <AppButton
                dsVariant="secondary"
                dsSize="sm"
                disabled={busy}
                onClick={() => void handleAgregarARuta()}
                data-testid="oper-ruta-agregar-ruta"
              >
                Agregar a ruta
              </AppButton>
            </span>
          </Tooltip>
        )}
      </Stack>
      <AgregarARutaOperDialog
        open={dialogOpen}
        poolId={pendingPoolId}
        fechaOperativa={fecha}
        onClose={() => setDialogOpen(false)}
        onSuccess={() => void handleDialogSuccess()}
        onError={onError}
      />
    </>
  );
}
