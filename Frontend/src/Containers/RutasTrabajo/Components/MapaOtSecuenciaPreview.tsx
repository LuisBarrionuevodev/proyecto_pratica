import { useCallback, useEffect, useState } from "react";
import { Box, Stack, Typography } from "@mui/material";

import {
  getOrdenTrabajoSecuenciaPreview,
  patchOrdenTrabajoSecuencia,
  type IOrdenTrabajoSecuenciaPreview,
} from "../../../api/rutasTrabajoApi";
import { useAppSession } from "../../../auth/AppSessionProvider";
import { AppButton } from "../../../ui/AppButton";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

type Props = {
  itemsCount: number;
  readOnly?: boolean;
  onRefresh?: () => void;
};

/**
 * Cabecera de mapa final: preview estimado de OT (sin reserva) + edición admin del contador.
 */
export function MapaOtSecuenciaPreview({ itemsCount, readOnly = false, onRefresh }: Props) {
  const { role } = useAppSession();
  const isAdmin = role === "admin";
  const [preview, setPreview] = useState<IOrdenTrabajoSecuenciaPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (readOnly || itemsCount <= 0) {
      setPreview(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getOrdenTrabajoSecuenciaPreview(itemsCount);
      setPreview(data);
    } catch {
      setError("No se pudo cargar la secuencia OT.");
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }, [itemsCount, readOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSaveCounter = async () => {
    const parsed = Number(newValue.trim());
    if (!Number.isFinite(parsed) || parsed < 1) return;
    const r = reason.trim();
    if (!r) return;
    setSaving(true);
    try {
      await patchOrdenTrabajoSecuencia({ new_value: parsed, reason: r });
      setEditOpen(false);
      setNewValue("");
      setReason("");
      await load();
      onRefresh?.();
    } catch {
      setError("No se pudo actualizar el contador.");
    } finally {
      setSaving(false);
    }
  };

  if (readOnly) return null;

  const showRange =
    itemsCount > 0 && Boolean(preview?.first_display && preview?.last_display);

  return (
    <Box
      data-testid="mapa-ot-secuencia-preview"
      sx={{
        minWidth: 0,
        width: { xs: "100%", md: "auto" },
        textAlign: { xs: "left", md: "right" },
      }}
    >
      <Stack
        spacing={0.5}
        alignItems={{ xs: "flex-start", md: "flex-end" }}
        sx={{ minWidth: { md: 200 } }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontSize: "0.68rem" }}>
          Rango OT estimado
        </Typography>
        <Typography
          variant="body1"
          data-testid="mapa-ot-rango-valor"
          sx={{
            fontWeight: 700,
            fontVariantNumeric: "tabular-nums",
            color: GLASS_COLORS.textPrimary,
            lineHeight: 1.25,
          }}
        >
          {loading
            ? "…"
            : showRange
              ? `${preview!.first_display} → ${preview!.last_display}`
              : "—"}
        </Typography>
        {itemsCount > 0 ? (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
            {itemsCount} ítem{itemsCount === 1 ? "" : "s"} a publicar
          </Typography>
        ) : null}
        {showRange && preview!.skipped_count > 0 ? (
          <Typography variant="caption" color="warning.light" sx={{ display: "block", fontSize: "0.65rem" }}>
            {preview!.skipped_count} número{preview!.skipped_count === 1 ? "" : "s"} existente
            {preview!.skipped_count === 1 ? "" : "s"} será omitido
          </Typography>
        ) : null}
        {isAdmin ? (
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            disabled={loading}
            onClick={() => setEditOpen(true)}
            sx={{ mt: 0.5, width: { xs: "100%", md: "auto" } }}
          >
            Editar
          </AppButton>
        ) : null}
      </Stack>
      {error ? (
        <Typography variant="caption" color="error.light" sx={{ mt: 0.5, display: "block" }}>
          {error}
        </Typography>
      ) : null}

      <ConfirmDialog
        open={editOpen}
        onClose={() => !saving && setEditOpen(false)}
        onConfirm={() => void handleSaveCounter()}
        title="Reposicionar inicio de secuencia OT"
        confirmLabel="Guardar"
        loading={saving}
      >
        <Stack spacing={1.5} sx={{ pt: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Cursor actual: <strong>{preview?.next_display ?? "—"}</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            La próxima OT se buscará desde este número. Los números ya utilizados se omitirán
            automáticamente.
          </Typography>
          <input
            type="number"
            min={1}
            placeholder="Nuevo inicio de búsqueda"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            style={{ padding: 8, borderRadius: 6, border: "1px solid #ccc" }}
          />
          <textarea
            placeholder="Motivo (obligatorio)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            style={{ padding: 8, borderRadius: 6, border: "1px solid #ccc", resize: "vertical" }}
          />
        </Stack>
      </ConfirmDialog>
    </Box>
  );
}
