import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  type IActuacionesPendientesItem,
} from "../../../api/actuacionesPendientesApi";
import { getCurrentMonthRange } from "../../../utils/dateRange";
import { DARK_TABLE_CONFIG } from "../styles/actuacionesTableStyles";

const PendientesExpedienteView = () => {
  type SourceTab = "notificacion" | "comprobacion";
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [desde, setDesde] = useState(defaultRange.desde);
  const [hasta, setHasta] = useState(defaultRange.hasta);
  const [sourceTab, setSourceTab] = useState<SourceTab>("notificacion");
  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<IActuacionesPendientesItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [expNumero, setExpNumero] = useState("");
  const [expAnio, setExpAnio] = useState(new Date().getFullYear().toString());
  const [prorrogaDias, setProrrogaDias] = useState("0");
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(desde, hasta, sourceTab);
      setItems(resp.items);
      setTotal(resp.meta.total);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar pendientes de expediente");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [desde, hasta, sourceTab]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const openModal = (row: IActuacionesPendientesItem) => {
    setSelected(row);
    setExpNumero(row.expediente_numero || "");
    setExpAnio(row.expediente_anio ? String(row.expediente_anio) : String(new Date().getFullYear()));
    setProrrogaDias("0");
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
  };

  const handleSave = async () => {
    if (!selected) return;
    if (!expNumero.trim() || !expAnio.trim()) {
      setError("Número y año de expediente son obligatorios");
      return;
    }

    const anioNum = Number(expAnio);
    if (!Number.isInteger(anioNum) || expAnio.length !== 4) {
      setError("El año de expediente debe tener 4 dígitos");
      return;
    }

    let prorrogaNum: number | undefined = undefined;
    if (selected.source_type === "NOTIFICACION") {
      const parsed = Number(prorrogaDias);
      if (!Number.isInteger(parsed) || parsed < 0) {
        setError("Prórroga (días) debe ser un entero mayor o igual a 0");
        return;
      }
      prorrogaNum = parsed;
    }

    setSaving(true);
    setError(null);
    try {
      await createExpedienteDesdeActuacion(selected.id, {
        expediente_numero: expNumero.trim(),
        expediente_anio: anioNum,
        source_type: selected.source_type,
        prorroga_dias: prorrogaNum,
      });
      closeModal();
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo completar el expediente");
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => {
      const baseColumns: MRT_ColumnDef<IActuacionesPendientesItem>[] = [
        { accessorKey: "fecha_actuacion", header: "Fecha", size: 120 },
        { accessorKey: "orden_trabajo_numero", header: "OT", size: 110 },
      ];

      const locationColumns: MRT_ColumnDef<IActuacionesPendientesItem>[] = [
        { accessorKey: "calle", header: "Calle", size: 200 },
        { accessorKey: "numero", header: "Número", size: 120 },
        { accessorKey: "rubro_nombre", header: "Rubro", size: 180 },
      ];

      const actionColumn: MRT_ColumnDef<IActuacionesPendientesItem> = {
        id: "acciones",
        header: "Acciones",
        size: 160,
        Cell: ({ row }) => (
          <Button variant="contained" size="small" onClick={() => openModal(row.original)}>
            Completar expediente
          </Button>
        ),
      };

      if (sourceTab === "notificacion") {
        return [
          ...baseColumns,
          { accessorKey: "acta_notificacion_num", header: "Acta notificación", size: 180 },
          ...locationColumns,
          {
            id: "motivos_notificacion",
            header: "Motivos notificación",
            size: 260,
            accessorFn: (row) =>
              [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
                .filter(Boolean)
                .join(" | "),
          },
          actionColumn,
        ];
      }

      return [
        ...baseColumns,
        { accessorKey: "acta_comprobacion_num", header: "Acta comprobación", size: 180 },
        ...locationColumns,
        { accessorKey: "comprobacion_motivo", header: "Motivo comprobación", size: 240 },
        actionColumn,
      ];
    },
    [sourceTab]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: items,
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1 }}>
        Total pendientes: {total}
      </Typography>
    ),
  });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        <TextField
          size="small"
          label="Desde"
          type="date"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          size="small"
          label="Hasta"
          type="date"
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="contained" onClick={loadData}>
          Filtrar
        </Button>
      </Box>

      <Tabs
        value={sourceTab}
        onChange={(_, value: SourceTab) => setSourceTab(value)}
        sx={{ marginTop: -1 }}
      >
        <Tab value="notificacion" label="Notificación" />
        <Tab value="comprobacion" label="Comprobación" />
      </Tabs>

      {error && <Alert severity="error">{error}</Alert>}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <MaterialReactTable table={table} />
      )}

      <Dialog open={modalOpen} onClose={closeModal} fullWidth maxWidth="sm">
        <DialogTitle>Completar expediente</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="Número de expediente"
            value={expNumero}
            onChange={(e) => setExpNumero(e.target.value)}
            fullWidth
            required
          />
          <TextField
            label="Año de expediente"
            type="number"
            value={expAnio}
            onChange={(e) => setExpAnio(e.target.value)}
            fullWidth
            required
          />
          {selected?.source_type === "NOTIFICACION" && (
            <TextField
              label="Prórroga (días)"
              type="number"
              value={prorrogaDias}
              onChange={(e) => setProrrogaDias(e.target.value)}
              fullWidth
              required
              helperText="Se suma al plazo base de 5 días de la notificación."
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeModal} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>
            {saving ? "Guardando..." : "Guardar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PendientesExpedienteView;
