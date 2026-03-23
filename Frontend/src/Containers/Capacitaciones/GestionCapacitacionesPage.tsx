import { useCallback, useEffect, useMemo, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import EditIcon from "@mui/icons-material/Edit";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import SaveIcon from "@mui/icons-material/Save";
import {
  Alert,
  Box,
  FormControlLabel,
  Grid,
  IconButton,
  Snackbar,
  Stack,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import { AppButton, AppDialog, AppSelect, AppTextField, CardGlass } from "../../ui";
import { COLORS } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import { getInitialCapacitacionesMock } from "./mocks/capacitacionesMock";
import type {
  CapacitacionFormValues,
  CapacitacionRow,
  ParticipanteCapacitacion,
} from "./types/capacitaciones.types";

const MESES = [
  { value: 1, label: "Enero" },
  { value: 2, label: "Febrero" },
  { value: 3, label: "Marzo" },
  { value: 4, label: "Abril" },
  { value: 5, label: "Mayo" },
  { value: 6, label: "Junio" },
  { value: 7, label: "Julio" },
  { value: 8, label: "Agosto" },
  { value: 9, label: "Septiembre" },
  { value: 10, label: "Octubre" },
  { value: 11, label: "Noviembre" },
  { value: 12, label: "Diciembre" },
];

const ANIOS = [2023, 2024, 2025, 2026].map((y) => ({ value: y, label: String(y) }));

const emptyForm: CapacitacionFormValues = {
  nombre: "",
  fechaInicio: "",
  sede: "",
  cantPromotores: "",
};

const MAX_PROMOTORES = 12;

function clampPromotorCount(raw: string): number {
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.min(MAX_PROMOTORES, n);
}

function resizePromotorSlots(prev: string[], n: number): string[] {
  const next = prev.slice(0, n);
  while (next.length < n) next.push("");
  return next;
}

/**
 * Gestión de capacitaciones (mock): período, formulario con N promotores, MRT con panel de participantes.
 */
export default function GestionCapacitacionesPage() {
  const [rows, setRows] = useState<CapacitacionRow[]>(() => getInitialCapacitacionesMock());
  const [mes, setMes] = useState(3);
  const [anio, setAnio] = useState(2024);
  const [form, setForm] = useState<CapacitacionFormValues>(emptyForm);
  const [promotorInputs, setPromotorInputs] = useState<string[]>([]);

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<CapacitacionRow | null>(null);
  const [editForm, setEditForm] = useState<CapacitacionFormValues>(emptyForm);
  const [editPromotorInputs, setEditPromotorInputs] = useState<string[]>([]);

  const [partOpen, setPartOpen] = useState(false);
  const [capIdForPart, setCapIdForPart] = useState<string | null>(null);
  const [part, setPart] = useState({
    nombre: "",
    apellido: "",
    dni: "",
    telefono: "",
    mail: "",
    lugarTrabajo: "",
    examenAprobado: false,
    nota: "",
  });

  const [snack, setSnack] = useState<string | null>(null);

  const nPromotoresAlta = useMemo(() => clampPromotorCount(form.cantPromotores), [form.cantPromotores]);

  useEffect(() => {
    setPromotorInputs((prev) => resizePromotorSlots(prev, nPromotoresAlta));
  }, [nPromotoresAlta]);

  const nPromotoresEdicion = useMemo(() => clampPromotorCount(editForm.cantPromotores), [editForm.cantPromotores]);

  useEffect(() => {
    if (!editOpen) return;
    setEditPromotorInputs((prev) => resizePromotorSlots(prev, nPromotoresEdicion));
  }, [nPromotoresEdicion, editOpen]);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      const d = new Date(r.fechaInicio);
      return d.getMonth() + 1 === mes && d.getFullYear() === anio;
    });
  }, [rows, mes, anio]);

  const totalParticipantes = useMemo(
    () => filtered.reduce((acc, r) => acc + r.participantes.length, 0),
    [filtered]
  );

  const onRegistrar = useCallback(() => {
    if (!form.nombre.trim() || !form.fechaInicio || !form.sede.trim()) {
      setSnack("Completá nombre, fecha y sede.");
      return;
    }
    if (nPromotoresAlta <= 0) {
      setSnack("Indicá al menos un promotor (cantidad > 0).");
      return;
    }
    const promotores = promotorInputs
      .slice(0, nPromotoresAlta)
      .map((s) => s.trim())
      .filter(Boolean);
    if (promotores.length !== nPromotoresAlta) {
      setSnack("Completá el nombre de cada promotor.");
      return;
    }
    const id = `cap-${Date.now()}`;
    setRows((prev) => [
      {
        id,
        nombre: form.nombre.trim(),
        fechaInicio: form.fechaInicio,
        sede: form.sede.trim(),
        promotores,
        participantes: [],
      },
      ...prev,
    ]);
    setForm(emptyForm);
    setPromotorInputs([]);
    setSnack("Evento registrado (mock, solo en pantalla).");
  }, [form, nPromotoresAlta, promotorInputs]);

  const openEdit = useCallback((row: CapacitacionRow) => {
    setEditing(row);
    setEditForm({
      nombre: row.nombre,
      fechaInicio: row.fechaInicio,
      sede: row.sede,
      cantPromotores: String(Math.max(1, row.promotores.length)),
    });
    setEditPromotorInputs(resizePromotorSlots([...row.promotores], Math.max(1, row.promotores.length)));
    setEditOpen(true);
  }, []);

  const saveEdit = useCallback(() => {
    if (!editing) return;
    if (nPromotoresEdicion <= 0) {
      setSnack("La cantidad de promotores debe ser mayor a 0.");
      return;
    }
    const promotores = editPromotorInputs
      .slice(0, nPromotoresEdicion)
      .map((s) => s.trim())
      .filter(Boolean);
    if (promotores.length !== nPromotoresEdicion) {
      setSnack("Completá el nombre de cada promotor.");
      return;
    }
    setRows((prev) =>
      prev.map((r) =>
        r.id === editing.id
          ? {
              ...r,
              nombre: editForm.nombre.trim(),
              fechaInicio: editForm.fechaInicio,
              sede: editForm.sede.trim(),
              promotores,
            }
          : r
      )
    );
    setEditOpen(false);
    setEditing(null);
    setSnack("Cambios guardados (mock).");
  }, [editing, editForm, editPromotorInputs, nPromotoresEdicion]);

  const deleteRow = useCallback((id: string) => {
    if (!window.confirm("¿Eliminar esta capacitación del listado mock?")) return;
    setRows((prev) => prev.filter((r) => r.id !== id));
    setSnack("Registro eliminado (mock).");
  }, []);

  const openAddParticipant = useCallback((capId: string) => {
    setCapIdForPart(capId);
    setPart({
      nombre: "",
      apellido: "",
      dni: "",
      telefono: "",
      mail: "",
      lugarTrabajo: "",
      examenAprobado: false,
      nota: "",
    });
    setPartOpen(true);
  }, []);

  const saveParticipant = useCallback(() => {
    if (!capIdForPart || !part.nombre.trim() || !part.apellido.trim() || !part.dni.trim()) {
      setSnack("Nombre, apellido y DNI son obligatorios.");
      return;
    }
    const p: ParticipanteCapacitacion = {
      id: `p-${Date.now()}`,
      nombre: part.nombre.trim(),
      apellido: part.apellido.trim(),
      dni: part.dni.trim(),
      telefono: part.telefono.trim(),
      mail: part.mail.trim(),
      lugarTrabajo: part.lugarTrabajo.trim(),
      examenAprobado: part.examenAprobado,
      nota: part.nota.trim() || null,
    };
    setRows((prev) =>
      prev.map((r) => (r.id === capIdForPart ? { ...r, participantes: [...r.participantes, p] } : r))
    );
    setPartOpen(false);
    setCapIdForPart(null);
    setSnack("Participante añadido (mock).");
  }, [capIdForPart, part]);

  const removeParticipant = useCallback((capId: string, partId: string) => {
    setRows((prev) =>
      prev.map((r) =>
        r.id === capId ? { ...r, participantes: r.participantes.filter((p) => p.id !== partId) } : r
      )
    );
  }, []);

  const columns = useMemo<MRT_ColumnDef<CapacitacionRow>[]>(
    () => [
      { accessorKey: "nombre", header: "CAPACITACIÓN", size: 280 },
      { accessorKey: "sede", header: "SEDE", size: 200 },
      {
        id: "promotores",
        header: "PROMOTORES",
        size: 140,
        accessorFn: (row) => row.promotores.length,
        Cell: ({ row }) => String(row.original.promotores.length),
      },
      { accessorKey: "fechaInicio", header: "FECHA INICIO", size: 120 },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: filtered,
    getRowId: (r) => r.id,
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableExpanding: true,
    getRowCanExpand: () => true,
    renderDetailPanel: ({ row }) => (
      <Box
        sx={{
          px: 2,
          py: 2,
          backgroundColor: COLORS.rowOdd,
          borderTop: `1px solid ${COLORS.border}`,
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }} flexWrap="wrap" gap={1}>
          <Typography
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.1em",
              color: COLORS.white,
            }}
          >
            PARTICIPANTES ({row.original.participantes.length})
          </Typography>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            startIcon={<PersonAddIcon sx={{ fontSize: 18 }} />}
            onClick={() => openAddParticipant(row.original.id)}
          >
            Añadir participante
          </AppButton>
        </Stack>
        {row.original.participantes.length === 0 ? (
          <Typography sx={{ fontSize: "12px", color: "rgba(255,255,255,0.45)" }}>
            Sin participantes cargados.
          </Typography>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Box component="table" sx={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
              <Box component="thead">
                <Box component="tr" sx={{ borderBottom: `1px solid ${COLORS.border}` }}>
                  {["Nombre", "Apellido", "DNI", "Teléfono", "Mail", "Lugar trabajo", "Examen", "Nota", ""].map(
                    (h) => (
                      <Box
                        component="th"
                        key={h}
                        sx={{
                          textAlign: "left",
                          fontSize: "10px",
                          fontWeight: 700,
                          letterSpacing: "0.08em",
                          color: "rgba(255,255,255,0.5)",
                          py: 0.75,
                          pr: 1,
                        }}
                      >
                        {h}
                      </Box>
                    )
                  )}
                </Box>
              </Box>
              <Box component="tbody">
                {row.original.participantes.map((p) => (
                  <Box
                    component="tr"
                    key={p.id}
                    sx={{ borderBottom: `1px solid ${COLORS.border}`, "&:hover": { bgcolor: "rgba(255,255,255,0.03)" } }}
                  >
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.nombre}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.apellido}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.dni}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.telefono || "—"}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.mail || "—"}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.lugarTrabajo || "—"}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.examenAprobado ? "Sí" : "No"}
                    </Box>
                    <Box component="td" sx={{ py: 1, pr: 1, fontSize: "12px", color: COLORS.white }}>
                      {p.nota ?? "—"}
                    </Box>
                    <Box component="td" sx={{ py: 1, textAlign: "right" }}>
                      <Tooltip title="Quitar (mock)">
                        <IconButton
                          size="small"
                          onClick={() => removeParticipant(row.original.id, p.id)}
                          sx={{ color: COLORS.error }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    ),
    localization: {
      expand: "Expandir",
      collapse: "Contraer",
    },
    initialState: {
      density: "compact",
      pagination: { pageSize: 10, pageIndex: 0 },
      expanded: { "cap-001": true },
    },
    enableRowActions: true,
    positionActionsColumn: "last",
    displayColumnDefOptions: {
      "mrt-row-actions": { header: "ACCIONES", size: 100 },
    },
    renderRowActions: ({ row }) => (
      <Stack direction="row" spacing={0.25}>
        <Tooltip title="Editar">
          <IconButton
            size="small"
            onClick={() => openEdit(row.original)}
            sx={{ color: COLORS.white, "&:hover": { color: COLORS.primary } }}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Eliminar">
          <IconButton
            size="small"
            onClick={() => deleteRow(row.original.id)}
            sx={{ color: COLORS.white, "&:hover": { color: COLORS.error } }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
    ),
  });

  const modalFieldSx = {
    "& .MuiInputLabel-root": { fontFamily: '"Tactic Sans", sans-serif', textTransform: "uppercase", fontSize: "11px" },
  };

  return (
    <Stack
      spacing={2}
      sx={{
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        px: { xs: 1.5, sm: 2 },
        pt: 1,
        pb: 2,
      }}
    >
      <CardGlass contentPadding="md">
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          alignItems={{ md: "center" }}
          justifyContent="space-between"
        >
          <Stack direction="row" spacing={1.5} flexWrap="wrap" alignItems="center">
            <AppSelect
              appearance="glass"
              size="small"
              label="Mes"
              sx={{ minWidth: 140 }}
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              options={MESES.map((m) => ({ value: m.value, label: m.label }))}
            />
            <AppSelect
              appearance="glass"
              size="small"
              label="Año"
              sx={{ minWidth: 100 }}
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value))}
              options={ANIOS}
            />
            <Typography sx={{ fontFamily: '"Tactic Sans", sans-serif', fontSize: "13px", color: COLORS.white }}>
              <Box component="span" sx={{ color: "rgba(255,255,255,0.55)", mr: 0.5 }}>
                TOTAL CAPACITACIONES:
              </Box>
              <strong>{filtered.length}</strong>
            </Typography>
            <Typography sx={{ fontFamily: '"Tactic Sans", sans-serif', fontSize: "13px" }}>
              <Box component="span" sx={{ color: "rgba(255,255,255,0.55)", mr: 0.5 }}>
                PARTICIPANTES:
              </Box>
              <Box component="strong" sx={{ color: COLORS.primary }}>
                {totalParticipantes}
              </Box>
            </Typography>
          </Stack>
          <AppButton
            dsVariant="secondary"
            startIcon={<DownloadIcon />}
            onClick={() => setSnack("Descarga de reporte mensual (mock — sin archivo).")}
            sx={{ fontWeight: 600, alignSelf: { xs: "stretch", md: "center" } }}
          >
            Descargar reporte mensual
          </AppButton>
        </Stack>
      </CardGlass>

      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 4 }}>
          <CardGlass contentPadding="md" sx={{ height: "100%" }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: "8px",
                  bgcolor: "rgba(1,102,255,0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <AddIcon sx={{ color: COLORS.primary, fontSize: 22 }} />
              </Box>
              <Box>
                <Typography
                  sx={{
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontSize: "11px",
                    fontWeight: 700,
                    letterSpacing: "0.12em",
                    color: COLORS.white,
                  }}
                >
                  NUEVA CAPACITACIÓN
                </Typography>
                <Typography sx={{ fontSize: "11px", color: "rgba(255,255,255,0.45)" }}>
                  Registro de actividad (mock)
                </Typography>
              </Box>
            </Stack>
            <Stack spacing={1.5}>
              <AppTextField
                appearance="glass"
                fullWidth
                size="small"
                label="Nombre de capacitación"
                placeholder="Ej: Introducción a Ley Orgánica"
                value={form.nombre}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                sx={modalFieldSx}
              />
              <AppTextField
                appearance="glass"
                fullWidth
                size="small"
                type="date"
                label="Fecha de inicio"
                value={form.fechaInicio}
                onChange={(e) => setForm((f) => ({ ...f, fechaInicio: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                sx={modalFieldSx}
              />
              <AppTextField
                appearance="glass"
                fullWidth
                size="small"
                label="Sede / ubicación"
                placeholder="Sala A"
                value={form.sede}
                onChange={(e) => setForm((f) => ({ ...f, sede: e.target.value }))}
                sx={modalFieldSx}
              />
              <AppTextField
                appearance="glass"
                fullWidth
                size="small"
                label="Cantidad de promotores"
                type="number"
                value={form.cantPromotores}
                onChange={(e) => setForm((f) => ({ ...f, cantPromotores: e.target.value }))}
                inputProps={{ min: 0, max: MAX_PROMOTORES }}
                sx={modalFieldSx}
              />
              {nPromotoresAlta > 0 && (
                <Stack spacing={1}>
                  <Typography sx={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.1em", color: "rgba(255,255,255,0.5)" }}>
                    NOMBRE POR PROMOTOR
                  </Typography>
                  {promotorInputs.slice(0, nPromotoresAlta).map((val, idx) => (
                    <AppTextField
                      key={idx}
                      appearance="glass"
                      fullWidth
                      size="small"
                      label={`Promotor ${idx + 1}`}
                      value={val}
                      onChange={(e) => {
                        const v = e.target.value;
                        setPromotorInputs((prev) => {
                          const next = [...prev];
                          next[idx] = v;
                          return next;
                        });
                      }}
                      sx={modalFieldSx}
                    />
                  ))}
                </Stack>
              )}
              <AppButton
                dsVariant="primary"
                fullWidth
                startIcon={<SaveIcon />}
                onClick={onRegistrar}
                sx={{ fontWeight: 700, letterSpacing: "0.06em", mt: 1 }}
              >
                Registrar evento
              </AppButton>
            </Stack>
          </CardGlass>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          <CardGlass contentPadding="sm" sx={{ overflow: "hidden" }}>
            <Typography
              sx={{
                px: 1,
                pt: 0.5,
                pb: 1,
                fontFamily: '"Tactic Sans", sans-serif',
                fontSize: "11px",
                fontWeight: 700,
                letterSpacing: "0.12em",
                color: "rgba(255,255,255,0.7)",
              }}
            >
              LISTADO OPERATIVO
            </Typography>
            <MaterialReactTable table={table} />
            <Typography
              variant="caption"
              sx={{ display: "block", px: 1, pt: 1, color: "rgba(255,255,255,0.45)" }}
            >
              Mostrando {filtered.length} registro(s) del período (mock). Expandí una fila para ver participantes.
            </Typography>
          </CardGlass>
        </Grid>
      </Grid>

      <AppDialog
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Editar capacitación (mock)"
        maxWidth="sm"
        showCloseButton
        onCloseButtonClick={() => setEditOpen(false)}
        actions={
          <>
            <AppButton dsVariant="secondary" onClick={() => setEditOpen(false)}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" onClick={saveEdit} startIcon={<SaveIcon />}>
              Guardar
            </AppButton>
          </>
        }
      >
        <Stack spacing={1.5} sx={{ pt: 1 }}>
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Nombre"
            value={editForm.nombre}
            onChange={(e) => setEditForm((f) => ({ ...f, nombre: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            type="date"
            label="Fecha inicio"
            value={editForm.fechaInicio}
            onChange={(e) => setEditForm((f) => ({ ...f, fechaInicio: e.target.value }))}
            InputLabelProps={{ shrink: true }}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Sede"
            value={editForm.sede}
            onChange={(e) => setEditForm((f) => ({ ...f, sede: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Cantidad de promotores"
            type="number"
            value={editForm.cantPromotores}
            onChange={(e) => setEditForm((f) => ({ ...f, cantPromotores: e.target.value }))}
            inputProps={{ min: 1, max: MAX_PROMOTORES }}
            sx={modalFieldSx}
          />
          {nPromotoresEdicion > 0 && (
            <Stack spacing={1}>
              {editPromotorInputs.slice(0, nPromotoresEdicion).map((val, idx) => (
                <AppTextField
                  key={idx}
                  appearance="glass"
                  fullWidth
                  size="small"
                  label={`Promotor ${idx + 1}`}
                  value={val}
                  onChange={(e) => {
                    const v = e.target.value;
                    setEditPromotorInputs((prev) => {
                      const next = [...prev];
                      next[idx] = v;
                      return next;
                    });
                  }}
                  sx={modalFieldSx}
                />
              ))}
            </Stack>
          )}
        </Stack>
      </AppDialog>

      <AppDialog
        open={partOpen}
        onClose={() => setPartOpen(false)}
        title="Añadir participante (mock)"
        maxWidth="sm"
        showCloseButton
        onCloseButtonClick={() => setPartOpen(false)}
        actions={
          <>
            <AppButton dsVariant="secondary" onClick={() => setPartOpen(false)}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" onClick={saveParticipant}>
              Guardar
            </AppButton>
          </>
        }
      >
        <Stack spacing={1.5} sx={{ pt: 1 }}>
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Nombre"
            value={part.nombre}
            onChange={(e) => setPart((p) => ({ ...p, nombre: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Apellido"
            value={part.apellido}
            onChange={(e) => setPart((p) => ({ ...p, apellido: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="DNI"
            value={part.dni}
            onChange={(e) => setPart((p) => ({ ...p, dni: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Teléfono"
            value={part.telefono}
            onChange={(e) => setPart((p) => ({ ...p, telefono: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Mail"
            value={part.mail}
            onChange={(e) => setPart((p) => ({ ...p, mail: e.target.value }))}
            sx={modalFieldSx}
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Lugar de trabajo"
            value={part.lugarTrabajo}
            onChange={(e) => setPart((p) => ({ ...p, lugarTrabajo: e.target.value }))}
            sx={modalFieldSx}
          />
          <FormControlLabel
            control={
              <Switch
                checked={part.examenAprobado}
                onChange={(_, c) => setPart((p) => ({ ...p, examenAprobado: c }))}
                color="primary"
              />
            }
            label={
              <Typography sx={{ fontSize: "13px", color: COLORS.white, fontFamily: '"Tactic Sans", sans-serif' }}>
                Examen aprobado
              </Typography>
            }
          />
          <AppTextField
            appearance="glass"
            fullWidth
            size="small"
            label="Nota"
            value={part.nota}
            onChange={(e) => setPart((p) => ({ ...p, nota: e.target.value }))}
            sx={modalFieldSx}
          />
        </Stack>
      </AppDialog>

      <Snackbar
        open={!!snack}
        autoHideDuration={3200}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="info" onClose={() => setSnack(null)} sx={{ fontFamily: '"Tactic Sans", sans-serif' }}>
          {snack}
        </Alert>
      </Snackbar>
    </Stack>
  );
}
