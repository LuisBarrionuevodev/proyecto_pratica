import { memo, useCallback, useMemo, useState } from "react";
import { Box, Button, Divider, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";

import type {
  IRutaGrupoInspector,
  IRutaGrupoMin,
  IRutaIniciadorPendienteRow,
  IRutaItemMin,
} from "../../../api/rutasTrabajoApi";
import { AppButton } from "../../../ui";
import { RutasOperativaChip } from "./RutasOperativaChip";
import { MIN_INSPECTORES_POR_GRUPO_PUBLICAR } from "../utils/rutaPublicarReadiness";
import {
  asignacionItemRowNeutralButtonSx,
  rutasAsignacionNeutralContainedButtonSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalGrupoPaperSx,
  rutasInstitutionalItemPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import {
  distritoOperativoDesdeItemYPool,
  etiquetaDomicilioDesdeItemYPool,
  rubroOperativoDesdeItemYPool,
  tipoEtiquetaDesdeItemYPool,
} from "../utils/rutaItemOperativoDesdeItemYPool";
import { detalleOperativoTexto } from "../utils/iniciadorDetalleOperativo";

interface Props {
  grupos: IRutaGrupoMin[];
  items: IRutaItemMin[];
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => Promise<void>;
}

const MOVER_A_FIELD_SX = {
  minWidth: { sm: 180 },
  maxWidth: { sm: 280 },
} as const;

function etiquetaInspectorEnLinea(ins: IRutaGrupoInspector): string {
  const nom = ins.inspector_nombre?.trim();
  if (nom) return nom;
  const leg = ins.inspector_legajo?.trim();
  if (leg) return `Leg. ${leg}`;
  return "Inspector";
}

type RutaGrupoItemRowProps = {
  item: IRutaItemMin;
  iniciador: IRutaIniciadorPendienteRow | undefined;
  target: number | "";
  canMove: boolean;
  moveTargets: IRutaGrupoMin[];
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
};

const RutaGrupoItemRow = memo(function RutaGrupoItemRow({
  item,
  iniciador,
  target,
  canMove,
  moveTargets,
  onMoveTargetChange,
  onMoverItem,
  onQuitarItem,
}: RutaGrupoItemRowProps) {
  const direccion = etiquetaDomicilioDesdeItemYPool(item, iniciador);
  const rubro = rubroOperativoDesdeItemYPool(item, iniciador);
  const distritoNombre = distritoOperativoDesdeItemYPool(item, iniciador);
  const tipoLabel = tipoEtiquetaDesdeItemYPool(item, iniciador);
  const detalle = detalleOperativoTexto(iniciador ?? item);

  return (
    <Paper elevation={0} sx={rutasInstitutionalItemPaperSx}>
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
        {direccion}
      </Typography>
      {detalle ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.35, lineHeight: 1.35 }}>
          {detalle}
        </Typography>
      ) : null}
      <Stack direction="row" spacing={0.7} sx={{ mt: 0.6 }} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="caption" color="text.secondary">
          {distritoNombre ? `${rubro} · ${distritoNombre}` : rubro}
        </Typography>
        <RutasOperativaChip label={tipoLabel} />
      </Stack>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 0.8 }} alignItems="stretch" flexWrap="wrap" useFlexGap>
        <Box sx={{ width: { xs: "100%", sm: "auto" }, minWidth: { sm: 180 }, maxWidth: { sm: 280 } }}>
          <TextField
            select
            fullWidth
            size="small"
            label="Mover a"
            value={target}
            onChange={(e) => {
              const val = e.target.value ? Number(e.target.value) : "";
              onMoveTargetChange(item.id, val);
            }}
            sx={MOVER_A_FIELD_SX}
            disabled={!canMove}
          >
            <MenuItem value="">Seleccionar</MenuItem>
            {moveTargets.map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.nombre}
              </MenuItem>
            ))}
          </TextField>
        </Box>
        <Button
          type="button"
          variant="contained"
          size="medium"
          disableElevation
          onClick={() => {
            if (typeof target === "number") void onMoverItem(item, target);
          }}
          disabled={!canMove || typeof target !== "number"}
          sx={asignacionItemRowNeutralButtonSx}
        >
          Mover
        </Button>
        <AppButton dsVariant="danger" dsSize="md" onClick={() => void onQuitarItem(item)}>
          Quitar
        </AppButton>
      </Stack>
    </Paper>
  );
});

type GrupoRutaSectionProps = {
  grupo: IRutaGrupoMin;
  groupItems: IRutaItemMin[];
  expanded: boolean;
  moveTargets: IRutaGrupoMin[];
  canMove: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  targetForItem: Record<number, number | "">;
  onToggleExpanded: (grupoId: number) => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
};

const GrupoRutaSection = memo(function GrupoRutaSection({
  grupo,
  groupItems,
  expanded,
  moveTargets,
  canMove,
  iniciadorById,
  targetForItem,
  onToggleExpanded,
  onEditarInspectores,
  onEliminarGrupo,
  onMoveTargetChange,
  onMoverItem,
  onQuitarItem,
}: GrupoRutaSectionProps) {
  const accent = `hsl(${(grupo.id * 61) % 360} 75% 58%)`;

  return (
    <Paper elevation={0} sx={rutasInstitutionalGrupoPaperSx(accent)}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems="stretch" spacing={1}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{grupo.nombre}</Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            <RutasOperativaChip label={`${groupItems.length} items`} color="primary" />
            <RutasOperativaChip
              label={`${grupo.inspectores.length} inspectores`}
              color={grupo.inspectores.length < MIN_INSPECTORES_POR_GRUPO_PUBLICAR ? "warning" : "default"}
            />
          </Stack>
        </Box>
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap justifyContent="flex-end">
          <Button type="button" variant="contained" size="small" disableElevation onClick={() => onToggleExpanded(grupo.id)} sx={rutasAsignacionNeutralContainedButtonSx}>
            {expanded ? "Ocultar items" : "Gestionar items"}
          </Button>
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => onEditarInspectores(grupo)}>Inspectores</AppButton>
          <AppButton dsVariant="danger" dsSize="sm" onClick={() => void onEliminarGrupo(grupo)}>Eliminar</AppButton>
        </Stack>
      </Stack>
      <Divider sx={{ my: 1.2, ...rutasInstitutionalDividerSx }} />
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.4 }}>
        {grupo.inspectores.length > 0 ? grupo.inspectores.map((i) => etiquetaInspectorEnLinea(i)).join(", ") : "Sin inspectores"}
      </Typography>
      <Stack spacing={1} sx={{ mt: 1.5 }}>
        {groupItems.length === 0 ? (
          <Typography variant="body2" color="text.secondary">Sin items asignados.</Typography>
        ) : expanded ? (
          groupItems.map((item) => (
            <RutaGrupoItemRow
              key={item.id}
              item={item}
              iniciador={iniciadorById[item.iniciador_ruta_id]}
              target={targetForItem[item.id] ?? ""}
              canMove={canMove}
              moveTargets={moveTargets}
              onMoveTargetChange={onMoveTargetChange}
              onMoverItem={onMoverItem}
              onQuitarItem={onQuitarItem}
            />
          ))
        ) : null}
      </Stack>
    </Paper>
  );
});

function PanelGruposRutaInner({
  grupos,
  items,
  iniciadorById,
  onEditarInspectores,
  onEliminarGrupo,
  onMoverItem,
  onQuitarItem,
}: Props) {
  const [targetByItem, setTargetByItem] = useState<Record<number, number | "">>({});
  const [expandedByGrupo, setExpandedByGrupo] = useState<Record<number, boolean>>({});

  const itemsByGrupoId = useMemo(() => {
    const m = new Map<number, IRutaItemMin[]>();
    for (const i of items) {
      if (i.deleted_at) continue;
      const list = m.get(i.ruta_grupo_id);
      if (list) list.push(i);
      else m.set(i.ruta_grupo_id, [i]);
    }
    return m;
  }, [items]);

  const moveTargetsByGrupoId = useMemo(() => {
    const map = new Map<number, IRutaGrupoMin[]>();
    for (const g of grupos) {
      map.set(g.id, grupos.filter((x) => x.id !== g.id));
    }
    return map;
  }, [grupos]);

  const canMove = grupos.length > 1;

  const handleMoveTargetChange = useCallback((itemId: number, value: number | "") => {
    setTargetByItem((prev) => ({ ...prev, [itemId]: value }));
  }, []);

  const toggleGrupoExpanded = useCallback((grupoId: number) => {
    setExpandedByGrupo((prev) => ({ ...prev, [grupoId]: !(prev[grupoId] ?? false) }));
  }, []);

  return (
    <Box sx={{ maxHeight: { xs: "none", md: "min(52vh, 560px)" }, overflowY: { xs: "visible", md: "auto" }, pr: { md: 0.5 }, ...rutasInstitutionalScrollSx }}>
      <Stack spacing={1.2}>
        {grupos.map((grupo) => {
          const groupItems = itemsByGrupoId.get(grupo.id) ?? [];
          const targetForItem: Record<number, number | ""> = {};
          for (const it of groupItems) {
            targetForItem[it.id] = targetByItem[it.id] ?? "";
          }
          return (
            <GrupoRutaSection
              key={grupo.id}
              grupo={grupo}
              groupItems={groupItems}
              expanded={expandedByGrupo[grupo.id] ?? false}
              moveTargets={moveTargetsByGrupoId.get(grupo.id) ?? []}
              canMove={canMove}
              iniciadorById={iniciadorById}
              targetForItem={targetForItem}
              onToggleExpanded={toggleGrupoExpanded}
              onEditarInspectores={onEditarInspectores}
              onEliminarGrupo={onEliminarGrupo}
              onMoveTargetChange={handleMoveTargetChange}
              onMoverItem={onMoverItem}
              onQuitarItem={onQuitarItem}
            />
          );
        })}
      </Stack>
    </Box>
  );
}

const PanelGruposRuta = memo(PanelGruposRutaInner);
export default PanelGruposRuta;
