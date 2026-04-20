import { memo, useCallback, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import { AppButton } from "../../../ui";
import {
  rutasAsignacionNeutralContainedButtonSx,
  rutasInstitutionalDividerSx,
  rutasInstitutionalGrupoPaperSx,
  rutasInstitutionalItemPaperSx,
  rutasInstitutionalScrollSx,
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

type OtUiKind = "sin_guardar" | "pendiente_guardar" | "guardada";

function otUiState(
  item: IRutaItemMin,
  draftRaw: string
): { kind: OtUiKind; chipLabel: string; chipColor: "default" | "warning" | "success"; helperText: string } {
  const persisted = (item.orden_trabajo?.numero_acta ?? "").trim();
  const draft = draftRaw.trim();
  const hasPersistedId = item.orden_trabajo_id != null;

  if (hasPersistedId && draft === persisted) {
    return {
      kind: "guardada",
      chipLabel: "OT guardada",
      chipColor: "success",
      helperText: "Guardada en servidor.",
    };
  }
  if (draft !== persisted) {
    return {
      kind: "pendiente_guardar",
      chipLabel: "OT pendiente de guardar",
      chipColor: "warning",
      helperText: "Confirmar con «Guardar OT».",
    };
  }
  return {
    kind: "sin_guardar",
    chipLabel: "OT no guardada",
    chipColor: "default",
    helperText: "Solo números. Requiere guardar para continuar.",
  };
}

const OT_FIELD_SX = { width: { xs: "100%", sm: 160 }, minWidth: 0 } as const;
const OT_FORM_HELPER_PROPS = { sx: { maxWidth: 320, m: 0, mt: 0.5 } } as const;

type RutaGrupoItemRowProps = {
  item: IRutaItemMin;
  iniciador: IRutaIniciadorPendienteRow | undefined;
  otDraft: string;
  target: number | "";
  savingThis: boolean;
  canMove: boolean;
  moveTargets: IRutaGrupoMin[];
  onOtDraftChange: (itemId: number, value: string) => void;
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onGuardarOt: (item: IRutaItemMin, otDraft: string) => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
};

/**
 * Fila de ítem expandida: memoizada para no re-renderizar el resto de ítems al editar OT de uno solo.
 */
type GrupoRutaSectionProps = {
  grupo: IRutaGrupoMin;
  groupItems: IRutaItemMin[];
  expanded: boolean;
  moveTargets: IRutaGrupoMin[];
  canMove: boolean;
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>;
  /** Solo borradores/targets de ítems de este grupo (comparación fina en memo). */
  otDraftForItem: Record<number, string>;
  targetForItem: Record<number, number | "">;
  /** `savingOtItemId` acotado a este grupo (evita re-render en otros grupos al guardar). */
  savingItemIdInSection: number | null;
  onToggleExpanded: (grupoId: number) => void;
  onEditarInspectores: (grupo: IRutaGrupoMin) => void;
  onEliminarGrupo: (grupo: IRutaGrupoMin) => Promise<void>;
  onOtDraftChange: (itemId: number, value: string) => void;
  onMoveTargetChange: (itemId: number, value: number | "") => void;
  onGuardarOt: (item: IRutaItemMin, otDraft: string) => void;
  onMoverItem: (item: IRutaItemMin, targetGrupoId: number) => void | Promise<void>;
  onQuitarItem: (item: IRutaItemMin) => void | Promise<void>;
};

function grupoRutaSectionPropsAreEqual(prev: GrupoRutaSectionProps, next: GrupoRutaSectionProps): boolean {
  if (prev.grupo !== next.grupo) return false;
  if (prev.groupItems !== next.groupItems) return false;
  if (prev.expanded !== next.expanded) return false;
  if (prev.moveTargets !== next.moveTargets) return false;
  if (prev.canMove !== next.canMove) return false;
  if (prev.iniciadorById !== next.iniciadorById) return false;
  if (prev.savingItemIdInSection !== next.savingItemIdInSection) return false;
  if (prev.onToggleExpanded !== next.onToggleExpanded) return false;
  if (prev.onEditarInspectores !== next.onEditarInspectores) return false;
  if (prev.onEliminarGrupo !== next.onEliminarGrupo) return false;
  if (prev.onOtDraftChange !== next.onOtDraftChange) return false;
  if (prev.onMoveTargetChange !== next.onMoveTargetChange) return false;
  if (prev.onGuardarOt !== next.onGuardarOt) return false;
  if (prev.onMoverItem !== next.onMoverItem) return false;
  if (prev.onQuitarItem !== next.onQuitarItem) return false;
  for (const it of prev.groupItems) {
    const id = it.id;
    if ((prev.otDraftForItem[id] ?? "") !== (next.otDraftForItem[id] ?? "")) return false;
    if ((prev.targetForItem[id] ?? "") !== (next.targetForItem[id] ?? "")) return false;
  }
  return true;
}

/**
 * Un grupo del panel: memo con igualdad por ítem para no re-ejecutar cabecera/lista de otros grupos al tipear OT.
 */
const GrupoRutaSection = memo(function GrupoRutaSection({
  grupo,
  groupItems,
  expanded,
  moveTargets,
  canMove,
  iniciadorById,
  otDraftForItem,
  targetForItem,
  savingItemIdInSection,
  onToggleExpanded,
  onEditarInspectores,
  onEliminarGrupo,
  onOtDraftChange,
  onMoveTargetChange,
  onGuardarOt,
  onMoverItem,
  onQuitarItem,
}: GrupoRutaSectionProps) {
  const accent = `hsl(${(grupo.id * 61) % 360} 75% 58%)`;

  return (
    <Paper elevation={0} sx={rutasInstitutionalGrupoPaperSx(accent)}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        spacing={1}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {grupo.nombre}
          </Typography>
          <Stack direction="row" spacing={0.75} sx={{ mt: 0.5 }}>
            <Chip size="small" label={`${groupItems.length} items`} color="primary" variant="outlined" />
            <Chip size="small" label={`${grupo.inspectores.length} inspectores`} variant="outlined" />
          </Stack>
        </Box>
        <Stack
          direction="row"
          spacing={0.75}
          flexWrap="wrap"
          useFlexGap
          justifyContent={{ xs: "flex-start", sm: "flex-end" }}
        >
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => onToggleExpanded(grupo.id)}>
            {expanded ? "Ocultar items" : "Gestionar items"}
          </AppButton>
          <Button
            variant="contained"
            size="small"
            disableElevation
            onClick={() => onEditarInspectores(grupo)}
            sx={rutasAsignacionNeutralContainedButtonSx}
          >
            Inspectores
          </Button>
          <AppButton dsVariant="danger" dsSize="sm" onClick={() => void onEliminarGrupo(grupo)}>
            Eliminar
          </AppButton>
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
            const otDraft = otDraftForItem[item.id] ?? "";
            const target = targetForItem[item.id] ?? "";
            const savingThis = savingItemIdInSection === item.id;
            return (
              <RutaGrupoItemRow
                key={item.id}
                item={item}
                iniciador={iniciador}
                otDraft={otDraft}
                target={target}
                savingThis={savingThis}
                canMove={canMove}
                moveTargets={moveTargets}
                onOtDraftChange={onOtDraftChange}
                onMoveTargetChange={onMoveTargetChange}
                onGuardarOt={onGuardarOt}
                onMoverItem={onMoverItem}
                onQuitarItem={onQuitarItem}
              />
            );
          })
        ) : null}
      </Stack>
    </Paper>
  );
}, grupoRutaSectionPropsAreEqual);

const RutaGrupoItemRow = memo(function RutaGrupoItemRow({
  item,
  iniciador,
  otDraft,
  target,
  savingThis,
  canMove,
  moveTargets,
  onOtDraftChange,
  onMoveTargetChange,
  onGuardarOt,
  onMoverItem,
  onQuitarItem,
}: RutaGrupoItemRowProps) {
  const otUi = useMemo(() => otUiState(item, otDraft), [item, otDraft]);
  const puedeGuardarOt = otDraft.trim().length > 0 && !savingThis;

  const direccion =
    iniciador?.domicilio_texto ??
    `${iniciador?.domicilio?.calle ?? "-"} ${iniciador?.domicilio?.numero ?? ""}`.trim();
  const rubro = iniciador?.rubro_nombre ?? iniciador?.domicilio?.rubro ?? "Sin rubro";
  const distritoNombre = iniciador?.distrito_nombre ?? iniciador?.domicilio?.distrito_nombre ?? null;
  const tipoLabel = iniciador?.badges?.tipo_label ?? iniciador?.tipo_iniciador ?? "SIN TIPO";

  return (
    <Paper elevation={0} sx={rutasInstitutionalItemPaperSx}>
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
        {direccion || `Iniciador #${item.iniciador_ruta_id}`}
      </Typography>
      <Stack direction="row" spacing={0.7} sx={{ mt: 0.6 }} alignItems="center" flexWrap="wrap">
        <Typography variant="caption" color="text.secondary">
          {distritoNombre ? `${rubro} · ${distritoNombre}` : rubro}
        </Typography>
        <Chip label={tipoLabel} size="small" variant="outlined" />
        <Chip label={`#${item.iniciador_ruta_id}`} size="small" variant="outlined" />
        <Chip label={otUi.chipLabel} size="small" color={otUi.chipColor} variant="outlined" />
      </Stack>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={0.8}
        sx={{ mt: 0.8 }}
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        flexWrap="wrap"
      >
        <TextField
          size="small"
          label="OT"
          value={otDraft}
          onChange={(e) => onOtDraftChange(item.id, e.target.value)}
          sx={OT_FIELD_SX}
          helperText={otUi.helperText}
          FormHelperTextProps={OT_FORM_HELPER_PROPS}
        />
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          loading={savingThis}
          disabled={!puedeGuardarOt}
          onClick={() => onGuardarOt(item, otDraft)}
          sx={{ alignSelf: { xs: "flex-start", sm: "center" }, mt: { xs: 0, sm: 0.25 } }}
        >
          {savingThis ? "Guardando…" : "Guardar OT"}
        </AppButton>
        <TextField
          select
          size="small"
          label="Mover a"
          value={target}
          onChange={(e) => {
            const val = e.target.value ? Number(e.target.value) : "";
            onMoveTargetChange(item.id, val);
          }}
          sx={{ minWidth: 150 }}
          disabled={!canMove}
        >
          <MenuItem value="">Seleccionar</MenuItem>
          {moveTargets.map((g) => (
            <MenuItem key={g.id} value={g.id}>
              {g.nombre}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="contained"
          size="small"
          disableElevation
          onClick={() => {
            if (typeof target === "number") void onMoverItem(item, target);
          }}
          disabled={!canMove || typeof target !== "number"}
          sx={rutasAsignacionNeutralContainedButtonSx}
        >
          Mover
        </Button>
        <AppButton dsVariant="danger" dsSize="sm" onClick={() => void onQuitarItem(item)}>
          Quitar
        </AppButton>
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
  onGuardarOtItem,
}: Props) {
  const [targetByItem, setTargetByItem] = useState<Record<number, number | "">>({});
  const [expandedByGrupo, setExpandedByGrupo] = useState<Record<number, boolean>>({});
  const [otDraftByItem, setOtDraftByItem] = useState<Record<number, string>>({});
  const [savingOtItemId, setSavingOtItemId] = useState<number | null>(null);

  const itemsSinOtPersistida = useMemo(
    () => items.filter((i) => !i.deleted_at && i.orden_trabajo_id == null),
    [items]
  );

  /** Un solo paso O(n): evita `items.filter` por grupo en cada render. */
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

  /** Lista de destino para el select «Mover a» por grupo (misma referencia mientras `grupos` no cambie). */
  const moveTargetsByGrupoId = useMemo(() => {
    const map = new Map<number, IRutaGrupoMin[]>();
    for (const g of grupos) {
      map.set(
        g.id,
        grupos.filter((x) => x.id !== g.id)
      );
    }
    return map;
  }, [grupos]);

  const canMove = grupos.length > 1;

  const handleOtDraftChange = useCallback((itemId: number, value: string) => {
    setOtDraftByItem((prev) => ({ ...prev, [itemId]: value }));
  }, []);

  const handleMoveTargetChange = useCallback((itemId: number, value: number | "") => {
    setTargetByItem((prev) => ({ ...prev, [itemId]: value }));
  }, []);

  const handleGuardarOt = useCallback(
    (item: IRutaItemMin, otDraft: string) => {
      void (async () => {
        setSavingOtItemId(item.id);
        try {
          const ok = await onGuardarOtItem(item, otDraft);
          if (ok) {
            setOtDraftByItem((prev) => {
              const next = { ...prev };
              delete next[item.id];
              return next;
            });
          }
        } finally {
          setSavingOtItemId((id) => (id === item.id ? null : id));
        }
      })();
    },
    [onGuardarOtItem]
  );

  const toggleGrupoExpanded = useCallback((grupoId: number) => {
    setExpandedByGrupo((prev) => ({
      ...prev,
      [grupoId]: !(prev[grupoId] ?? false),
    }));
  }, []);

  return (
    <Box
      sx={{
        maxHeight: { xs: "none", md: "min(52vh, 560px)" },
        overflowY: { xs: "visible", md: "auto" },
        overflowX: "hidden",
        pr: { md: 0.5 },
        ...rutasInstitutionalScrollSx,
      }}
    >
      <Stack spacing={1.2}>
        {itemsSinOtPersistida.length > 0 ? (
          <Alert severity="info" variant="outlined" sx={{ borderRadius: 2, py: 0.5 }}>
            <Typography variant="body2" component="span" sx={{ lineHeight: 1.4, fontSize: "0.8125rem" }}>
              {itemsSinOtPersistida.length} ítem{itemsSinOtPersistida.length === 1 ? "" : "s"} sin OT guardada. Expandir
              grupo y usar «Guardar OT».
            </Typography>
          </Alert>
        ) : null}
        {grupos.map((grupo) => {
          const groupItems = itemsByGrupoId.get(grupo.id) ?? [];
          const expanded = expandedByGrupo[grupo.id] ?? false;
          const moveTargets = moveTargetsByGrupoId.get(grupo.id) ?? [];
          const otDraftForItem: Record<number, string> = {};
          const targetForItem: Record<number, number | ""> = {};
          for (const it of groupItems) {
            otDraftForItem[it.id] = otDraftByItem[it.id] ?? it.orden_trabajo?.numero_acta ?? "";
            targetForItem[it.id] = targetByItem[it.id] ?? "";
          }
          const savingItemIdInSection =
            savingOtItemId != null && groupItems.some((i) => i.id === savingOtItemId) ? savingOtItemId : null;

          return (
            <GrupoRutaSection
              key={grupo.id}
              grupo={grupo}
              groupItems={groupItems}
              expanded={expanded}
              moveTargets={moveTargets}
              canMove={canMove}
              iniciadorById={iniciadorById}
              otDraftForItem={otDraftForItem}
              targetForItem={targetForItem}
              savingItemIdInSection={savingItemIdInSection}
              onToggleExpanded={toggleGrupoExpanded}
              onEditarInspectores={onEditarInspectores}
              onEliminarGrupo={onEliminarGrupo}
              onOtDraftChange={handleOtDraftChange}
              onMoveTargetChange={handleMoveTargetChange}
              onGuardarOt={handleGuardarOt}
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
