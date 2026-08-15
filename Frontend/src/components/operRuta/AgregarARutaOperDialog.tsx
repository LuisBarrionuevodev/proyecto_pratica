import { useCallback, useEffect, useMemo, useState } from "react";
import { CircularProgress, Stack, Typography } from "@mui/material";

import { getRutaTrabajoDetail, listRutasBorrador, type IRutaGrupoMin, type IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { agregarDesdePoolRuta } from "../../api/rutaPoolDiaApi";
import { AppButton, AppSelect } from "../../ui";
import { AppDialog } from "../../ui/AppDialog";
import { parseApiError } from "../../utils/parseApiError";

export type AgregarARutaOperDialogProps = {
  open: boolean;
  poolId: number | null;
  fechaOperativa: string;
  onClose: () => void;
  onSuccess: () => void;
  onError: (message: string) => void;
};

/**
 * Selector conservador de ruta BORRADOR + grupo antes de `agregar-desde-pool`.
 */
export function AgregarARutaOperDialog({
  open,
  poolId,
  fechaOperativa,
  onClose,
  onSuccess,
  onError,
}: AgregarARutaOperDialogProps) {
  const [loadingRutas, setLoadingRutas] = useState(false);
  const [loadingGrupos, setLoadingGrupos] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rutas, setRutas] = useState<IRutaTrabajo[]>([]);
  const [grupos, setGrupos] = useState<IRutaGrupoMin[]>([]);
  const [rutaId, setRutaId] = useState("");
  const [grupoId, setGrupoId] = useState("");

  useEffect(() => {
    if (!open) return;
    setRutaId("");
    setGrupoId("");
    setGrupos([]);
    let cancelled = false;
    setLoadingRutas(true);
    void listRutasBorrador({ fecha: fechaOperativa, per_page: 50 })
      .then((resp) => {
        if (cancelled) return;
        setRutas(resp.items ?? []);
      })
      .catch((err) => {
        if (cancelled) return;
        onError(parseApiError(err, "No se pudieron cargar rutas borrador.").message);
        setRutas([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingRutas(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, fechaOperativa, onError]);

  useEffect(() => {
    if (!open || !rutaId) {
      setGrupos([]);
      setGrupoId("");
      return;
    }
    let cancelled = false;
    setLoadingGrupos(true);
    void getRutaTrabajoDetail(Number(rutaId))
      .then((detail) => {
        if (cancelled) return;
        const gs = detail.grupos ?? [];
        setGrupos(gs);
        setGrupoId(gs.length === 1 ? String(gs[0].id) : "");
      })
      .catch((err) => {
        if (cancelled) return;
        onError(parseApiError(err, "No se pudieron cargar los grupos de la ruta.").message);
        setGrupos([]);
        setGrupoId("");
      })
      .finally(() => {
        if (!cancelled) setLoadingGrupos(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, rutaId, onError]);

  const rutaOptions = useMemo(
    () => [
      { value: "", label: "Seleccioná ruta borrador" },
      ...rutas.map((r) => ({
        value: String(r.id),
        label: r.display_name?.trim() || `Ruta #${r.numero} · ${r.fecha}`,
      })),
    ],
    [rutas]
  );

  const grupoOptions = useMemo(
    () => [
      { value: "", label: "Seleccioná grupo" },
      ...grupos.map((g) => ({ value: String(g.id), label: g.nombre?.trim() || `Grupo #${g.id}` })),
    ],
    [grupos]
  );

  const handleConfirm = useCallback(async () => {
    if (poolId == null) {
      onError("No se encontró el ítem en el pool del día.");
      return;
    }
    if (!rutaId) {
      onError("Seleccioná una ruta borrador.");
      return;
    }
    if (!grupoId) {
      onError("Seleccioná un grupo de la ruta.");
      return;
    }
    setSubmitting(true);
    try {
      await agregarDesdePoolRuta(Number(rutaId), {
        pool_ids: [poolId],
        grupo_id: Number(grupoId),
      });
      onSuccess();
      onClose();
    } catch (err) {
      onError(parseApiError(err, "No se pudo agregar el ítem a la ruta.").message);
    } finally {
      setSubmitting(false);
    }
  }, [poolId, rutaId, grupoId, onSuccess, onClose, onError]);

  const sinRutas = !loadingRutas && rutas.length === 0;

  return (
    <AppDialog open={open} onClose={onClose} title="Agregar a ruta borrador" maxWidth="sm" fullWidth>
      <Stack spacing={2} sx={{ pt: 0.5 }}>
        {loadingRutas ? (
          <Stack direction="row" alignItems="center" spacing={1}>
            <CircularProgress size={20} />
            <Typography variant="body2">Cargando rutas…</Typography>
          </Stack>
        ) : sinRutas ? (
          <Typography variant="body2" color="text.secondary">
            No hay ruta borrador disponible para la fecha operativa.
          </Typography>
        ) : (
          <>
            <AppSelect
              appearance="dense"
              label="Ruta"
              value={rutaId}
              onChange={(e) => setRutaId(String(e.target.value))}
              options={rutaOptions}
              fullWidth
            />
            {loadingGrupos ? (
              <Stack direction="row" alignItems="center" spacing={1}>
                <CircularProgress size={20} />
                <Typography variant="body2">Cargando grupos…</Typography>
              </Stack>
            ) : (
              <AppSelect
                appearance="dense"
                label="Grupo"
                value={grupoId}
                onChange={(e) => setGrupoId(String(e.target.value))}
                options={grupoOptions}
                disabled={!rutaId || grupos.length === 0}
                fullWidth
              />
            )}
            {rutaId && !loadingGrupos && grupos.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                La ruta no tiene grupos. Creá un grupo en Rutas de trabajo antes de asignar.
              </Typography>
            )}
          </>
        )}
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <AppButton dsVariant="ghost" dsSize="sm" onClick={onClose} disabled={submitting}>
            Cancelar
          </AppButton>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={() => void handleConfirm()}
            disabled={submitting || sinRutas || !poolId}
          >
            {submitting ? "Agregando…" : "Agregar a ruta"}
          </AppButton>
        </Stack>
      </Stack>
    </AppDialog>
  );
}
