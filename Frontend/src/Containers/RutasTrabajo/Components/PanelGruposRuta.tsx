import { useState } from "react";
import { Box, Button, Chip, Divider, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";

interface Props {
  grupos: IRutaGrupoMin[];
  items: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => Promise<void>;
  onEditarOtItem: (item: IRutaItemMin) => void;
}

const PanelGruposRuta = ({
  grupos,
  items,
  iniciadorById,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
  onEditarOtItem,
}: Props) => {
  const [targetByItem, setTargetByItem] = useState<Record<number, number | "">>({});

  return (
    <Stack spacing={1.5}>
      {grupos.map((grupo) => {
        const groupItems = items.filter((i) => i.ruta_grupo_id === grupo.id && !i.deleted_at);
        const accent = `hsl(${(grupo.id * 61) % 360} 75% 58%)`;
        return (
          <Paper
            key={grupo.id}
            variant="outlined"
            sx={{
              p: 1.5,
              borderColor: "rgba(98, 127, 182, 0.34)",
              background:
                "linear-gradient(180deg, rgba(19,29,52,0.95) 0%, rgba(11,18,34,0.98) 100%)",
              borderLeft: `4px solid ${accent}`,
            }}
          >
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
                <Button size="small" variant="outlined" onClick={() => onEditarInspectores(grupo)}>
                  Inspectores
                </Button>
                <Button size="small" color="error" variant="outlined" onClick={() => void onEliminarGrupo(grupo)}>
                  Eliminar
                </Button>
              </Stack>
            </Stack>
            <Divider sx={{ my: 1.2, borderColor: "rgba(124, 149, 193, 0.24)" }} />

            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {grupo.inspectores.length > 0
                ? grupo.inspectores.map((i) => i.inspector_nombre ?? `#${i.inspector_id}`).join(", ")
                : "Sin inspectores"}
            </Typography>

            <Stack spacing={1} sx={{ mt: 1.5 }}>
              {groupItems.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Sin items asignados.
                </Typography>
              ) : (
                groupItems.map((item) => {
                  const iniciador = iniciadorById[item.iniciador_ruta_id];
                  const direccion = `${iniciador?.domicilio?.calle ?? "-"} ${iniciador?.domicilio?.numero ?? ""}`.trim();
                  const canMove = grupos.length > 1;
                  const target = targetByItem[item.id] || "";
                  return (
                    <Paper
                      key={item.id}
                      sx={{ p: 1.2, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(90,114,152,0.22)" }}
                    >
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {direccion || `Iniciador #${item.iniciador_ruta_id}`}
                        </Typography>
                        <Chip label={`#${item.iniciador_ruta_id}`} size="small" variant="outlined" />
                      </Stack>

                      <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap">
                        <TextField size="small" label="OT" value={item.orden_trabajo?.numero_acta ?? ""} InputProps={{ readOnly: true }} sx={{ width: 130 }} />
                        <Button size="small" variant="outlined" onClick={() => onEditarOtItem(item)}>
                          Editar OT
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
              )}
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
};

export default PanelGruposRuta;
