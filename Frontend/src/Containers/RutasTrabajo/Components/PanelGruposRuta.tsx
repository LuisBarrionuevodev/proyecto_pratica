import { useState } from "react";
import { Box, Button, Chip, Divider, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import {
  rutasInstitutionalDividerSx,
  rutasInstitutionalGrupoPaperSx,
  rutasInstitutionalItemPaperSx,
} from "../styles/institutionalVisual";

interface Props {
  grupos: IRutaGrupoMin[];
  items: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => Promise<void>;
  onGuardarOtItem: (item: IRutaItemMin, numeroOt: string) => boolean | Promise<boolean>;
}

const PanelGruposRuta = ({
  grupos,
  items,
  iniciadorById,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onGuardarOtItem,
}: Props) => {
  const [targetByItem, setTargetByItem] = useState<Record<number, number | "">>({});
  const [expandedByGrupo, setExpandedByGrupo] = useState<Record<number, boolean>>({});
  const [otDraftByItem, setOtDraftByItem] = useState<Record<number, string>>({});

  return (
    <Stack spacing={1.2}>
      {grupos.map((grupo) => {
        const groupItems = items.filter((i) => i.ruta_grupo_id === grupo.id && !i.deleted_at);
        const expanded = expandedByGrupo[grupo.id] ?? false;
        const accent = `hsl(${(grupo.id * 61) % 360} 75% 58%)`;
        return (
          <Paper key={grupo.id} elevation={0} sx={rutasInstitutionalGrupoPaperSx(accent)}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {grupo.nombre}
                </Typography>
                <Stack direction="row" spacing={0.75} sx={{ mt: 0.5 }}>
                  <Chip size="small" label={`${groupItems.length} items`} color="primary" variant="outlined" />
                  <Chip size="small" label={`${grupo.inspectores.length} inspectores`} variant="outlined" />
                </Stack>
              </Box>
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  variant="contained"
                  onClick={() =>
                    setExpandedByGrupo((prev) => ({
                      ...prev,
                      [grupo.id]: !expanded,
                    }))
                  }
                >
                  {expanded ? "Ocultar items" : "Gestionar items"}
                </Button>
                <Button size="small" variant="outlined" onClick={() => onEditarInspectores(grupo)}>
                  Inspectores
                </Button>
                <Button size="small" color="error" variant="outlined" onClick={() => void onEliminarGrupo(grupo)}>
                  Eliminar
                </Button>
              </Stack>
            </Stack>
            <Divider sx={{ my: 1.2, ...rutasInstitutionalDividerSx }} />

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>
              {grupo.inspectores.length > 0
                ? grupo.inspectores.map((i) => i.inspector_nombre ?? `#${i.inspector_id}`).join(", ")
                : "Sin inspectores"}
            </Typography>

            <Stack spacing={1} sx={{ mt: 1.5 }}>
              {groupItems.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Sin items asignados.
                </Typography>
              ) : expanded ? (
                groupItems.map((item) => {
                  const iniciador = iniciadorById[item.iniciador_ruta_id];
                  const direccion =
                    iniciador?.domicilio_texto ??
                    `${iniciador?.domicilio?.calle ?? "-"} ${iniciador?.domicilio?.numero ?? ""}`.trim();
                  const rubro = iniciador?.rubro_nombre ?? iniciador?.domicilio?.rubro ?? "Sin rubro";
                  const distritoNombre = iniciador?.distrito_nombre ?? iniciador?.domicilio?.distrito_nombre ?? null;
                  const tipoLabel = iniciador?.badges?.tipo_label ?? iniciador?.tipo_iniciador ?? "SIN TIPO";
                  const canMove = grupos.length > 1;
                  const target = targetByItem[item.id] || "";
                  const otDraft = otDraftByItem[item.id] ?? item.orden_trabajo?.numero_acta ?? "";
                  return (
                    <Paper key={item.id} elevation={0} sx={rutasInstitutionalItemPaperSx}>
                      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                          {direccion || `Iniciador #${item.iniciador_ruta_id}`}
                      </Typography>
                      <Stack direction="row" spacing={0.7} sx={{ mt: 0.6 }} alignItems="center" flexWrap="wrap">
                        <Typography variant="caption" color="text.secondary">
                          {distritoNombre ? `${rubro} · ${distritoNombre}` : rubro}
                        </Typography>
                        <Chip label={tipoLabel} size="small" variant="outlined" />
                        <Chip label={`#${item.iniciador_ruta_id}`} size="small" variant="outlined" />
                      </Stack>
                      <Stack direction="row" spacing={0.8} sx={{ mt: 0.8 }} alignItems="center" flexWrap="wrap">
                        <TextField
                          size="small"
                          label="OT"
                          value={otDraft}
                          onChange={(e) =>
                            setOtDraftByItem((prev) => ({
                              ...prev,
                              [item.id]: e.target.value,
                            }))
                          }
                          sx={{ width: 140 }}
                        />
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => {
                            void (async () => {
                              const ok = await onGuardarOtItem(item, otDraft);
                              if (ok) {
                                setOtDraftByItem((prev) => {
                                  const next = { ...prev };
                                  delete next[item.id];
                                  return next;
                                });
                              }
                            })();
                          }}
                        >
                          Guardar OT
                        </Button>
                        <TextField
                          select
                          size="small"
                          label="Mover a"
                          value={target}
                          onChange={(e) => {
                            const val = e.target.value ? Number(e.target.value) : "";
                            setTargetByItem((prev) => ({ ...prev, [item.id]: val }));
                          }}
                          sx={{ minWidth: 150 }}
                          disabled={!canMove}
                        >
                          <MenuItem value="">Seleccionar</MenuItem>
                          {grupos
                            .filter((g) => g.id !== grupo.id)
                            .map((g) => (
                              <MenuItem key={g.id} value={g.id}>
                                {g.nombre}
                              </MenuItem>
                            ))}
                        </TextField>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            if (typeof target === "number") void onMoverItem(item, target);
                          }}
                          disabled={!canMove || typeof target !== "number"}
                        >
                          Mover
                        </Button>
                        <Button size="small" color="error" variant="outlined" onClick={() => void onQuitarItem(item)}>
                          Quitar
                        </Button>
                      </Stack>
                    </Paper>
                  );
                })
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {groupItems.length} items listos para gestionar.
                </Typography>
              )}
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
};

export default PanelGruposRuta;
