import { useCallback, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from "react";
import {
  Autocomplete,
  Box,
  Chip,
  CircularProgress,
  LinearProgress,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

import { startBatch, type GridRow } from "../../../api/gridApi";
import { fetchCompletarTrabajoCatalogsCached } from "../../CompletarTrabajos/hooks/completarTrabajoCatalogsCache";
import { mergeLegacyRubroNames } from "../../../utils/rubrosCatalogCache";
import { useAppFeedback } from "../../../components/feedback";
import { extractDataColumns, generateRowId } from "../utils/gridHelpers";
import { getDropdownOptions } from "../config/dropdownOptions";
import { dedupeInspectoresPreserveOrder } from "../utils/inspectoresGridHelpers";
import {
  mergeMotivosNotifCatalogStrings,
  MOTIVOS_NOTIFICACION_MAX,
  slotsToMotivosApi,
} from "../../../utils/motivosNotificacionSlots";
import { normalizeActuacionApiError } from "../../Actuaciones/validations/normalizeActuacionApiError";
import { notifyActuacionApiError } from "../../Actuaciones/utils/actuacionSaveFeedback";
import { getCargarActuacionChecklistV2ResetState } from "../utils/cargarActuacionModalLifecycle";
import { submitCargarActuacionNuevaRow } from "../utils/cargarActuacionNuevaSubmit";
import {
  CrudDialogHeader,
  CrudDialogSection,
  CrudGlassDialog,
  crudDialogActionsRowSx,
} from "../../../components/crudDialog";
import { DOC_MODAL_BLOCK_STACK_SPACING, DOC_MODAL_TEXT } from "../../../styles/documentalModalTokens";
import { GLASS_COLORS, moduleHeroCardSx } from "../../../styles/GlassStyles";
import { AppButton, AppSelect, AppTextField, CardGlass, type AppSelectOption } from "../../../ui";
import {
  InspeccionChecklistFields,
  isValidActaInspeccionNum,
} from "../../Actuaciones/Components/InspeccionChecklistFields";
import {
  PersonasSinCarnetField,
  isValidActaNotificacionNum,
} from "../../Actuaciones/Components/PersonasSinCarnetField";
import {
  estadosMapFromRow,
  itemsActaInspeccionWriteFromEstados,
  sortCatalogItems,
} from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import type { ChecklistUxValue } from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";

const tactic = '"Tactic Sans", sans-serif' as const;

/** Keys Glide (contrato `COLUMN_MAP_ACTUACIONES` / grilla). */
const GLIDE_KEYS = [
  "Fecha actuación",
  "Orden de trabajo",
  "Calle",
  "Número",
  "Rubro",
  "Apellido",
  "Nombre",
  "Razón social",
  "DNI",
  "Acta inspección",
  "Acta notificación",
  "Acta comprobación",
  "Motivo comprobación",
  "Acta clausura",
  "Acta decomiso",
  "Kilos decomiso",
] as const;

type GlideTextKey = (typeof GLIDE_KEYS)[number];

type TitularModo = "persona" | "razon_social";

function emptyTextFields(): Record<GlideTextKey, string> {
  return Object.fromEntries(GLIDE_KEYS.map((k) => [k, ""])) as Record<GlideTextKey, string>;
}

/** Misma columna flexible y labels que `CompletarTrabajoModal`. */
const col = { display: "flex", flexDirection: "column" as const, gap: 1.5 };
const labelMuted = { color: "rgba(255,255,255,0.5)", fontFamily: tactic } as const;

const modalAuxInputSx = {
  "& .MuiInputBase-input": { color: DOC_MODAL_TEXT },
  "& .MuiInputLabel-root": { color: "rgba(255,255,255,0.92)" },
  "& .MuiOutlinedInput-notchedOutline": { borderColor: "rgba(255,255,255,0.38)" },
  "& .MuiFormHelperText-root": { color: "rgba(255,255,255,0.88)" },
} as const;

const edicionGrid2ColSx = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
  alignItems: "end",
} as const;

function CargarActuacionBloque({ title, children }: { title: string; children: ReactNode }) {
  return (
    <CrudDialogSection title={title} variant="plain">
      {children}
    </CrudDialogSection>
  );
}

export function CargarActuacionNuevaModal() {
  const feedback = useAppFeedback();
  const [open, setOpen] = useState(false);
  const [rowId, setRowId] = useState(() => generateRowId());

  const [texts, setTexts] = useState<Record<GlideTextKey, string>>(emptyTextFields);
  const [notifMotivosSel, setNotifMotivosSel] = useState<string[]>([]);
  const [inspectoresList, setInspectoresList] = useState<string[]>([]);
  /** Texto de búsqueda en Autocomplete “agregar ítem”; se limpia tras cada selección para permitir otra búsqueda. */
  const [inspectoresAddInput, setInspectoresAddInput] = useState("");
  const [notifMotivosAddInput, setNotifMotivosAddInput] = useState("");
  const [titularModo, setTitularModo] = useState<TitularModo>("persona");

  const [batchId, setBatchId] = useState<string | null>(null);
  const [startingBatch, setStartingBatch] = useState(false);
  const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
  const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
  const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
  const [catalogMotivosComprobacion, setCatalogMotivosComprobacion] = useState<string[]>([]);
  const [catalogItemsActaInspeccion, setCatalogItemsActaInspeccion] = useState<
    IItemActaInspeccionCatalogItem[]
  >([]);
  const [checklistEstados, setChecklistEstados] = useState<Record<number, ChecklistUxValue>>({});
  const [personasSinCarnet, setPersonasSinCarnet] = useState("0");
  const [checklistItemsTouched, setChecklistItemsTouched] = useState(false);
  const [personasSinCarnetTouched, setPersonasSinCarnetTouched] = useState(false);
  const [catalogsReady, setCatalogsReady] = useState(false);
  /** True hasta que termine el primer fetch de catálogos (éxito o error); para paridad con preload de Completar trabajo. */
  const [catalogsBootstrapping, setCatalogsBootstrapping] = useState(true);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const catalogs = useMemo(
    () => ({
      inspectores: catalogInspectores,
      motivos: catalogMotivos,
      rubros: catalogRubros,
      tipos: [] as string[],
      contraproducencias: [] as string[],
      motivosComprobacion: catalogMotivosComprobacion,
    }),
    [catalogInspectores, catalogMotivos, catalogRubros, catalogMotivosComprobacion]
  );

  const motivosNotifCatalogSorted = useMemo(
    () => mergeMotivosNotifCatalogStrings(catalogMotivos, notifMotivosSel),
    [catalogMotivos, notifMotivosSel]
  );
  const motivosDisponiblesNueva = useMemo(
    () => motivosNotifCatalogSorted.filter((m) => !notifMotivosSel.includes(m)),
    [motivosNotifCatalogSorted, notifMotivosSel]
  );

  const rubroAutocompleteOptions = useMemo(
    () => mergeLegacyRubroNames(catalogRubros, texts["Rubro"]),
    [catalogRubros, texts["Rubro"]]
  );

  const inspectoresDisponiblesParaAgregar = useMemo(() => {
    const ya = new Set(inspectoresList.map((x) => x.trim()).filter(Boolean));
    return [...catalogInspectores].filter((n) => !ya.has(n)).sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
  }, [catalogInspectores, inspectoresList]);

  const ensureBatch = useCallback(async (): Promise<string | null> => {
    if (batchId) return batchId;
    setStartingBatch(true);
    try {
      const { batch_id } = await startBatch("actuaciones");
      setBatchId(batch_id);
      return batch_id;
    } catch (e: unknown) {
      const normalized = normalizeActuacionApiError(e, {
        fallbackMessage: "No se pudo iniciar el lote.",
      });
      notifyActuacionApiError(normalized, feedback);
      return null;
    } finally {
      setStartingBatch(false);
    }
  }, [batchId, feedback]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setCatalogsBootstrapping(true);
      try {
        const data = await fetchCompletarTrabajoCatalogsCached();
        if (cancelled) return;
        setCatalogInspectores(data.inspectores);
        setCatalogMotivos(data.motivos);
        setCatalogRubros(data.rubros);
        setCatalogMotivosComprobacion(data.motivosComprobacion);
        const items = sortCatalogItems(data.itemsActaInspeccion ?? []);
        setCatalogItemsActaInspeccion(items);
        setChecklistEstados(estadosMapFromRow({}, items));
        setCatalogsReady(true);
      } catch {
        if (!cancelled) {
          feedback.error("Error cargando catálogos. Probá de nuevo más tarde.");
          setCatalogsReady(false);
        }
      } finally {
        if (!cancelled) setCatalogsBootstrapping(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [feedback]);

  useEffect(() => {
    if (!open) return;
    void ensureBatch();
  }, [open, ensureBatch]);

  const resetForm = useCallback(() => {
    const checklistV2Reset = getCargarActuacionChecklistV2ResetState();
    setTexts(emptyTextFields());
    setNotifMotivosSel([]);
    setInspectoresList([]);
    setInspectoresAddInput("");
    setNotifMotivosAddInput("");
    setTitularModo("persona");
    setChecklistEstados(checklistV2Reset.checklistEstados);
    setPersonasSinCarnet(checklistV2Reset.personasSinCarnet);
    setChecklistItemsTouched(checklistV2Reset.checklistItemsTouched);
    setPersonasSinCarnetTouched(checklistV2Reset.personasSinCarnetTouched);
    setFieldErrors({});
    setRowId(generateRowId());
  }, []);

  const errorFor = useCallback((glideKey: string) => fieldErrors[glideKey] ?? "", [fieldErrors]);

  const clearFe = useCallback((glideKey: string) => {
    setFieldErrors((prev) => {
      if (!(glideKey in prev)) return prev;
      const next = { ...prev };
      delete next[glideKey];
      return next;
    });
  }, []);

  const handleTitularModoChange = useCallback(
    (_: MouseEvent<HTMLElement>, next: TitularModo | null) => {
      if (next == null || next === titularModo) return;
      if (next === "razon_social") {
        setTexts((prev) => ({ ...prev, Apellido: "", Nombre: "" }));
      } else {
        setTexts((prev) => ({ ...prev, "Razón social": "" }));
      }
      setTitularModo(next);
      ["Apellido", "Nombre", "Razón social"].forEach((k) => clearFe(k));
    },
    [titularModo, clearFe]
  );

  const buildGridRow = useCallback((): GridRow => {
    const kilosRaw = texts["Kilos decomiso"].trim();
    let kilos: number | null = null;
    if (kilosRaw !== "") {
      const n = Number(kilosRaw.replace(",", "."));
      kilos = Number.isFinite(n) ? n : null;
    }

    const row: GridRow = {
      _rowId: rowId,
      _state: "PENDIENTE",
      _cellErrors: {},
      Inspectores: dedupeInspectoresPreserveOrder(inspectoresList),
    };

    for (const k of GLIDE_KEYS) {
      if (k === "Kilos decomiso") {
        row["Kilos decomiso"] = kilos;
        continue;
      }
      if (titularModo === "persona" && k === "Razón social") {
        (row as Record<string, unknown>)["Razón social"] = null;
        continue;
      }
      if (titularModo === "razon_social" && (k === "Apellido" || k === "Nombre")) {
        (row as Record<string, unknown>)[k] = null;
        continue;
      }
      const t = texts[k].trim();
      (row as Record<string, unknown>)[k] = t === "" ? null : t;
    }

    const slots = slotsToMotivosApi(notifMotivosSel);
    (row as Record<string, unknown>)["Motivo notif 1"] = slots.m1 || null;
    (row as Record<string, unknown>)["Motivo notif 2"] = slots.m2 || null;
    (row as Record<string, unknown>)["Motivo notif 3"] = slots.m3 || null;

    if (checklistItemsTouched) {
      (row as Record<string, unknown>).items_acta_inspeccion =
        itemsActaInspeccionWriteFromEstados(checklistEstados, catalogItemsActaInspeccion);
    }
    if (personasSinCarnetTouched && isValidActaNotificacionNum(texts["Acta notificación"])) {
      const cantidad = parseInt(personasSinCarnet, 10);
      if (!Number.isNaN(cantidad) && cantidad >= 0) {
        (row as Record<string, unknown>).cantidad_personas_sin_carnet_sanidad = cantidad;
      }
    }

    return row;
  }, [
    personasSinCarnet,
    personasSinCarnetTouched,
    checklistItemsTouched,
    checklistEstados,
    inspectoresList,
    rowId,
    texts,
    titularModo,
    notifMotivosSel,
  ]);

  const toSelectOptions = (columnId: string): AppSelectOption[] =>
    getDropdownOptions(columnId, catalogs).map((label) => ({
      value: label,
      label: label === "" ? "—" : label,
    }));

  const handleSubmit = async () => {
    setFieldErrors({});

    const bid = await ensureBatch();
    if (!bid) return;

    setLoading(true);
    try {
      const gridRow = buildGridRow();
      const payload = extractDataColumns(gridRow) as Partial<GridRow>;
      await submitCargarActuacionNuevaRow({
        batchId: bid,
        rowId,
        payload,
        feedback,
        resetForm,
        closeModal: () => setOpen(false),
        setFieldErrors,
      });
    } finally {
      setLoading(false);
    }
  };

  const tryClose = () => {
    if (!loading) setOpen(false);
  };

  const setText = (key: GlideTextKey, value: string) => {
    setTexts((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Box sx={{ width: "100%", minWidth: 0, boxSizing: "border-box" }}>
      <CardGlass sx={{ ...moduleHeroCardSx, width: "100%", minWidth: 0 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "stretch", sm: "center" },
            gap: 2,
            minWidth: 0,
          }}
        >
          <Box sx={{ minWidth: 0, flex: { sm: "1 1 auto" } }}>
            <Typography
              sx={{
                fontFamily: tactic,
                fontWeight: 700,
                fontSize: "1rem",
                color: GLASS_COLORS.textPrimary,
                letterSpacing: "0.02em",
              }}
            >
              ¿Querés cargar una nueva actuación?
            </Typography>
            <Typography
              sx={{
                fontFamily: tactic,
                mt: 0.5,
                fontSize: "0.875rem",
                color: GLASS_COLORS.textMuted,
                lineHeight: 1.45,
              }}
            >
              Podés cargar actas de notificación y/o comprobación en el mismo envío. Validación y guardado con el mismo
              motor de lote que el resto del sistema (grid / backend).
            </Typography>
          </Box>
          <AppButton
            dsVariant="primary"
            onClick={() => {
              setFieldErrors({});
              setOpen(true);
            }}
            startIcon={<AddIcon />}
            sx={{ flexShrink: 0, alignSelf: { xs: "stretch", sm: "center" } }}
            disabled={(startingBatch && !batchId) || catalogsBootstrapping}
          >
            Nueva actuación
          </AppButton>
        </Box>
      </CardGlass>

      <CrudGlassDialog
        open={open}
        onClose={() => tryClose()}
        onCloseButtonClick={() => tryClose()}
        maxWidth="md"
        fullWidth
        title={
          <CrudDialogHeader
            domainChip="Cargar actuación"
            titulo="Nueva actuación"
            subtitulo="Datos operativos y actas del día"
          />
        }
        actions={
          <Box
            sx={{
              ...crudDialogActionsRowSx,
              width: "100%",
              justifyContent: "space-between",
              flexWrap: "wrap",
              rowGap: 1,
            }}
          >
            <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={resetForm}
                disabled={loading || catalogsBootstrapping}
              >
                Limpiar
              </AppButton>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={() => tryClose()}
                disabled={loading || catalogsBootstrapping}
              >
                Cancelar
              </AppButton>
            </Box>
            <AppButton
              dsVariant="primary"
              dsSize="sm"
              onClick={() => void handleSubmit()}
              loading={loading}
              disabled={loading || !catalogsReady || catalogsBootstrapping || (startingBatch && !batchId)}
            >
              Guardar actuación
            </AppButton>
          </Box>
        }
      >
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
        {open && catalogsBootstrapping && (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: 2 }}>
            <LinearProgress sx={{ borderRadius: 1 }} />
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5, py: 2 }}>
              <CircularProgress size={32} sx={{ color: "rgba(255,255,255,0.7)" }} />
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.55)", textAlign: "center" }}>
                Cargando catálogos…
              </Typography>
            </Box>
          </Box>
        )}

        {!catalogsBootstrapping && (
          <>
        {open && startingBatch && !batchId ? <LinearProgress sx={{ borderRadius: 1 }} /> : null}

        <CargarActuacionBloque title="Datos generales">
        <Box sx={{ ...col, width: "100%" }}>
          <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
            fullWidth
            required
            type="date"
            label="Fecha actuación"
            value={texts["Fecha actuación"]}
            onChange={(e) => {
              setText("Fecha actuación", e.target.value);
              clearFe("Fecha actuación");
            }}
            InputLabelProps={{ shrink: true }}
            error={Boolean(errorFor("Fecha actuación"))}
            helperText={errorFor("Fecha actuación") || undefined}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            required
            label="Orden de trabajo"
            value={texts["Orden de trabajo"]}
            onChange={(e) => {
              setText("Orden de trabajo", e.target.value);
              clearFe("Orden de trabajo");
            }}
            disabled={catalogsBootstrapping}
            error={Boolean(errorFor("Orden de trabajo"))}
            helperText={errorFor("Orden de trabajo") || undefined}
          />
          </Box>

          <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
            Inspectores
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
            {inspectoresList.length === 0 ? (
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
                —
              </Typography>
            ) : (
              inspectoresList.map((name, idx) => (
                <Chip
                  key={`${idx}-${name}`}
                  label={name}
                  size="small"
                  onDelete={() => {
                    setInspectoresList((prev) => prev.filter((_, i) => i !== idx));
                    clearFe("Inspectores");
                  }}
                  sx={{ bgcolor: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.92)" }}
                />
              ))
            )}
          </Box>
          <Autocomplete
            size="small"
            options={inspectoresDisponiblesParaAgregar}
            value={null}
            inputValue={inspectoresAddInput}
            onInputChange={(_, newInput, reason) => {
              if (reason === "input") setInspectoresAddInput(newInput);
              else if (reason === "clear" || reason === "reset") setInspectoresAddInput("");
            }}
            onChange={(_, value) => {
              if (value && !inspectoresList.includes(value)) {
                setInspectoresList((prev) => dedupeInspectoresPreserveOrder([...prev, value]));
                clearFe("Inspectores");
                setInspectoresAddInput("");
              }
            }}
            disabled={!catalogsReady || inspectoresDisponiblesParaAgregar.length === 0 || catalogsBootstrapping}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Agregar inspector"
                placeholder={catalogsReady ? "Catálogo" : "…"}
                sx={modalAuxInputSx}
                error={Boolean(errorFor("Inspectores"))}
                helperText={errorFor("Inspectores") || undefined}
              />
            )}
          />
        </Box>
        </CargarActuacionBloque>

        <CargarActuacionBloque title="Domicilio y establecimiento">
        <Box sx={{ ...col, width: "100%" }}>
          <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
            label="Calle"
            value={texts["Calle"]}
            onChange={(e) => {
              setText("Calle", e.target.value);
              clearFe("Calle");
            }}
            fullWidth
            error={Boolean(errorFor("Calle"))}
            helperText={errorFor("Calle") || undefined}
          />
          <AppTextField
            appearance="glass"
            label="Número"
            value={texts["Número"]}
            onChange={(e) => {
              setText("Número", e.target.value);
              clearFe("Número");
            }}
            fullWidth
            error={Boolean(errorFor("Número"))}
            helperText={errorFor("Número") || undefined}
          />
          </Box>
          <Autocomplete
            size="small"
            fullWidth
            options={rubroAutocompleteOptions}
            value={texts["Rubro"] || null}
            onChange={(_, next) => {
              setText("Rubro", next ?? "");
              clearFe("Rubro");
            }}
            disabled={!catalogsReady || catalogsBootstrapping}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Rubro"
                  placeholder="Buscar rubro…"
                  sx={modalAuxInputSx}
                  error={Boolean(errorFor("Rubro"))}
                helperText={errorFor("Rubro") || undefined}
              />
            )}
          />
        </Box>
        </CargarActuacionBloque>

        <CargarActuacionBloque title="Contribuyente / titular">
        <Box sx={{ ...col, width: "100%" }}>
          <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
            Titular
          </Typography>
          <ToggleButtonGroup
            exclusive
            value={titularModo}
            onChange={handleTitularModoChange}
            size="small"
            fullWidth
            sx={{
              "& .MuiToggleButton-root": {
                flex: 1,
                textTransform: "none",
                fontFamily: tactic,
                fontSize: "0.8125rem",
                color: "rgba(255,255,255,0.75)",
                borderColor: "rgba(255,255,255,0.2)",
              },
              "& .Mui-selected": {
                bgcolor: "rgba(255,255,255,0.12) !important",
                color: "rgba(255,255,255,0.95) !important",
              },
            }}
          >
            <ToggleButton value="persona">Contribuyente</ToggleButton>
            <ToggleButton value="razon_social">Razón social</ToggleButton>
          </ToggleButtonGroup>

          {titularModo === "persona" ? (
            <Box sx={edicionGrid2ColSx}>
              <AppTextField
                appearance="glass"
                label="Apellido"
                value={texts["Apellido"]}
                onChange={(e) => {
                  setText("Apellido", e.target.value);
                  clearFe("Apellido");
                }}
                fullWidth
                error={Boolean(errorFor("Apellido"))}
                helperText={errorFor("Apellido") || undefined}
              />
              <AppTextField
                appearance="glass"
                label="Nombre"
                value={texts["Nombre"]}
                onChange={(e) => {
                  setText("Nombre", e.target.value);
                  clearFe("Nombre");
                }}
                fullWidth
                error={Boolean(errorFor("Nombre"))}
                helperText={errorFor("Nombre") || undefined}
              />
            </Box>
          ) : (
            <AppTextField
              appearance="glass"
              label="Razón social"
              value={texts["Razón social"]}
              onChange={(e) => {
                setText("Razón social", e.target.value);
                clearFe("Razón social");
              }}
              fullWidth
              error={Boolean(errorFor("Razón social"))}
              helperText={errorFor("Razón social") || undefined}
            />
          )}

          <AppTextField
            appearance="glass"
            label="CUIT / DNI"
            value={texts["DNI"]}
            onChange={(e) => {
              setText("DNI", e.target.value);
              clearFe("DNI");
            }}
            fullWidth
            error={Boolean(errorFor("DNI"))}
            helperText={errorFor("DNI") || undefined}
          />
        </Box>
        </CargarActuacionBloque>

        <CargarActuacionBloque title="Actas labradas">
        <Box sx={{ ...col, width: "100%" }}>
          <AppTextField
            appearance="glass"
            label="N° acta de inspección"
            value={texts["Acta inspección"]}
            onChange={(e) => {
              setText("Acta inspección", e.target.value);
              clearFe("Acta inspección");
            }}
            fullWidth
            error={Boolean(errorFor("Acta inspección"))}
            helperText={errorFor("Acta inspección") || undefined}
          />
          <InspeccionChecklistFields
            appearance="glass"
            catalog={catalogItemsActaInspeccion}
            estados={checklistEstados}
            onEstadosChange={(estados) => {
              setChecklistEstados(estados);
              setChecklistItemsTouched(true);
              clearFe("items_acta_inspeccion");
            }}
            disabled={!isValidActaInspeccionNum(texts["Acta inspección"])}
            errors={{
              items: errorFor("items_acta_inspeccion"),
            }}
          />
          <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
            label="N° acta de notificación"
            value={texts["Acta notificación"]}
            onChange={(e) => {
              setText("Acta notificación", e.target.value);
              clearFe("Acta notificación");
            }}
            fullWidth
            error={Boolean(errorFor("Acta notificación"))}
            helperText={errorFor("Acta notificación") || undefined}
          />
          </Box>
          <Typography variant="caption" sx={{ ...labelMuted, display: "block" }}>
            Motivos de notificación (máx. {MOTIVOS_NOTIFICACION_MAX})
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
            {notifMotivosSel.length === 0 ? (
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
                —
              </Typography>
            ) : (
              notifMotivosSel.map((name, idx) => (
                <Chip
                  key={`${idx}-${name}`}
                  label={name}
                  size="small"
                  onDelete={() => {
                    setNotifMotivosSel((prev) => prev.filter((_, i) => i !== idx));
                    clearFe("Motivo notif 1");
                    clearFe("Motivo notif 2");
                    clearFe("Motivo notif 3");
                  }}
                  sx={{ bgcolor: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.92)" }}
                />
              ))
            )}
          </Box>
          <Autocomplete
            size="small"
            options={motivosDisponiblesNueva}
            value={null}
            inputValue={notifMotivosAddInput}
            onInputChange={(_, newInput, reason) => {
              if (reason === "input") setNotifMotivosAddInput(newInput);
              else if (reason === "clear" || reason === "reset") setNotifMotivosAddInput("");
            }}
            onChange={(_, value) => {
              if (value && !notifMotivosSel.includes(value) && notifMotivosSel.length < MOTIVOS_NOTIFICACION_MAX) {
                setNotifMotivosSel((prev) => [...prev, value]);
                clearFe("Motivo notif 1");
                clearFe("Motivo notif 2");
                clearFe("Motivo notif 3");
                setNotifMotivosAddInput("");
              }
            }}
            disabled={
              !catalogsReady ||
              catalogsBootstrapping ||
              motivosDisponiblesNueva.length === 0 ||
              notifMotivosSel.length >= MOTIVOS_NOTIFICACION_MAX
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Agregar motivo"
                placeholder={catalogsReady ? "Catálogo" : "…"}
                sx={modalAuxInputSx}
                error={Boolean(
                  errorFor("Motivo notif 1") || errorFor("Motivo notif 2") || errorFor("Motivo notif 3")
                )}
                helperText={
                  errorFor("Motivo notif 1") ||
                  errorFor("Motivo notif 2") ||
                  errorFor("Motivo notif 3") ||
                  undefined
                }
              />
            )}
          />
          <PersonasSinCarnetField
            appearance="glass"
            value={personasSinCarnet}
            onChange={(v) => {
              setPersonasSinCarnet(v);
              setPersonasSinCarnetTouched(true);
              clearFe("cantidad_personas_sin_carnet_sanidad");
            }}
            disabled={!isValidActaNotificacionNum(texts["Acta notificación"])}
            error={errorFor("cantidad_personas_sin_carnet_sanidad")}
          />
          <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
            label="N° acta de comprobación"
            value={texts["Acta comprobación"]}
            onChange={(e) => {
              setText("Acta comprobación", e.target.value);
              clearFe("Acta comprobación");
            }}
            fullWidth
            error={Boolean(errorFor("Acta comprobación"))}
            helperText={errorFor("Acta comprobación") || undefined}
          />
          <AppSelect
            appearance="glass"
            label="Motivo de comprobación"
            value={texts["Motivo comprobación"]}
            onChange={(e) => {
              setText("Motivo comprobación", String(e.target.value));
              clearFe("Motivo comprobación");
            }}
            fullWidth
            disabled={!catalogsReady || catalogsBootstrapping}
            options={toSelectOptions("Motivo comprobación")}
            error={Boolean(errorFor("Motivo comprobación"))}
            helperText={errorFor("Motivo comprobación") || undefined}
          />
          </Box>
          <Box sx={edicionGrid2ColSx}>
          <AppTextField
            appearance="glass"
            label="N° acta de clausura (opcional)"
            value={texts["Acta clausura"]}
            onChange={(e) => {
              setText("Acta clausura", e.target.value);
              clearFe("Acta clausura");
            }}
            fullWidth
            error={Boolean(errorFor("Acta clausura"))}
            helperText={errorFor("Acta clausura") || undefined}
          />
          <AppTextField
            appearance="glass"
            label="N° acta de decomiso"
            value={texts["Acta decomiso"]}
            onChange={(e) => {
              setText("Acta decomiso", e.target.value);
              clearFe("Acta decomiso");
            }}
            fullWidth
            error={Boolean(errorFor("Acta decomiso"))}
            helperText={errorFor("Acta decomiso") || undefined}
          />
          </Box>
          <AppTextField
            appearance="glass"
            label="Kilos decomisados"
            value={texts["Kilos decomiso"]}
            onChange={(e) => {
              setText("Kilos decomiso", e.target.value);
              clearFe("Kilos decomiso");
            }}
            fullWidth
            inputProps={{ inputMode: "decimal" }}
            error={Boolean(errorFor("Kilos decomiso"))}
            helperText={errorFor("Kilos decomiso") || undefined}
          />
        </Box>
        </CargarActuacionBloque>
          </>
        )}
        </Stack>
      </CrudGlassDialog>
    </Box>
  );
}
