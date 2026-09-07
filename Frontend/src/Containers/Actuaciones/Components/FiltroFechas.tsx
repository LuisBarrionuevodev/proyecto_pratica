import { Box, Divider, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchInspectores, fetchTiposActuacion } from "../../../api/gridApi";
import { AppButton, AppSelect, AppTextField } from "../../../ui";
import type { BandejaPeriodMode } from "../../../utils/bandejaFiltroPeriodUi";
import {
  BANDEJA_MESES_OPTS_WITH_EMPTY,
  bandejaDefaultMonthYear,
  bandejaYearOptions,
} from "../../../utils/bandejaFiltroPeriodUi";

import {
  filtroContainerStyles,
  filtroTitleStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroButtonsStyles,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroSectionTitleStyles,
} from "../styles/filtroStyles";
import type { IActuacionesListFilters } from "../../../api/actuacionesListApi";
import {
  ACTUACIONES_FILTRO_FORM_VACIO,
  ACTUACIONES_TEXTO_MIN_CHARS,
  validateActuacionesFiltroForm,
} from "../utils/buildActuacionesFiltroPayload";

export type ActuacionesFiltroPayload = IActuacionesListFilters;

interface FiltroFechasProps {
  onFiltrar: (filtros: IActuacionesListFilters) => void;
  onLimpiarLista?: () => void;
}

/**
 * Filtros de Actuaciones: datos + actas + período (PERF.1-A1 / A1.1).
 */
const FiltroFechas = ({ onFiltrar, onLimpiarLista }: FiltroFechasProps) => {
  const [form, setForm] = useState(ACTUACIONES_FILTRO_FORM_VACIO);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [catalogTipos, setCatalogTipos] = useState<string[]>([]);
  const [catalogInspectores, setCatalogInspectores] = useState<{ id: number; nombre: string }[]>(
    []
  );

  const defaultMonthYear = useMemo(() => bandejaDefaultMonthYear(), []);

  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [tipos, inspectores] = await Promise.all([
          fetchTiposActuacion(),
          fetchInspectores(),
        ]);
        setCatalogTipos([...new Set(tipos.items.map((t) => t.nombre))]);
        setCatalogInspectores(
          inspectores.items.map((i) => ({ id: i.id, nombre: i.nombre }))
        );
      } catch (error) {
        console.error("Error cargando catálogos de filtros:", error);
      }
    };
    void loadCatalogs();
  }, []);

  const patchForm = (patch: Partial<typeof form>) => {
    setForm((prev) => ({ ...prev, ...patch }));
    if (validationError) setValidationError(null);
  };

  const handlePeriodModeChange = (mode: BandejaPeriodMode) => {
    if (mode === "month") {
      patchForm({ periodMode: mode, desde: "", hasta: "" });
    } else {
      patchForm({ periodMode: mode, mes: "", anio: "" });
    }
  };

  const handleFiltrar = () => {
    const result = validateActuacionesFiltroForm(form);
    if (!result.ok) {
      setValidationError(result.error);
      return;
    }
    setValidationError(null);
    onFiltrar(result.payload);
  };

  const handleLimpiar = () => {
    setForm(ACTUACIONES_FILTRO_FORM_VACIO);
    setValidationError(null);
    onLimpiarLista?.();
  };

  const tipoOptions = [{ value: "", label: "Todos" }, ...catalogTipos.map((t) => ({ value: t, label: t }))];
  const inspectorOptions = [
    { value: "", label: "Todos" },
    ...catalogInspectores.map((i) => ({ value: String(i.id), label: i.nombre })),
  ];

  return (
    <Box sx={filtroContainerStyles}>
      <Typography sx={filtroTitleStyles}>Filtros de búsqueda</Typography>

      <Typography sx={filtroSectionTitleStyles}>Datos de la actuación</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Orden de Trabajo"
            value={form.ordenTrabajo}
            onChange={(e) => patchForm({ ordenTrabajo: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Domicilio (calle)"
            value={form.calleQ}
            onChange={(e) => patchForm({ calleQ: e.target.value })}
            placeholder={`Mín. ${ACTUACIONES_TEXTO_MIN_CHARS} caracteres`}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="DNI / CUIT"
            value={form.documentoQ}
            onChange={(e) => patchForm({ documentoQ: e.target.value })}
            placeholder={`Mín. ${ACTUACIONES_TEXTO_MIN_CHARS} caracteres`}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="Nombre / Razón social"
            value={form.contribuyenteQ}
            onChange={(e) => patchForm({ contribuyenteQ: e.target.value })}
            placeholder={`Mín. ${ACTUACIONES_TEXTO_MIN_CHARS} caracteres`}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Tipo de actuación"
            value={form.tipo}
            onChange={(e) => patchForm({ tipo: e.target.value })}
            variant="outlined"
            options={tipoOptions}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Inspector"
            value={form.inspectorId === "" ? "" : String(form.inspectorId)}
            onChange={(e) =>
              patchForm({
                inspectorId: e.target.value === "" ? "" : Number(e.target.value),
              })
            }
            variant="outlined"
            options={inspectorOptions}
          />
        </Box>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.12)", my: 2 }} />

      <Typography sx={filtroSectionTitleStyles}>Actas</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Acta Inspección"
            value={form.actaInspeccion}
            onChange={(e) => patchForm({ actaInspeccion: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Acta Notificación"
            value={form.actaNotificacion}
            onChange={(e) => patchForm({ actaNotificacion: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Acta Comprobación"
            value={form.actaComprobacion}
            onChange={(e) => patchForm({ actaComprobacion: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Acta Clausura"
            value={form.actaClausura}
            onChange={(e) => patchForm({ actaClausura: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            fullWidth
            label="N.º Acta Decomiso"
            value={form.actaDecomiso}
            onChange={(e) => patchForm({ actaDecomiso: e.target.value })}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleFiltrar();
            }}
          />
        </Box>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.12)", my: 2 }} />

      <Typography sx={filtroSectionTitleStyles}>Período</Typography>
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            fullWidth
            label="Vista de período"
            value={form.periodMode}
            onChange={(e) => handlePeriodModeChange(e.target.value as BandejaPeriodMode)}
            variant="outlined"
            options={[
              { value: "month", label: "Mes y año" },
              { value: "range", label: "Fecha desde / hasta" },
            ]}
          />
        </Box>
        {form.periodMode === "month" ? (
          <>
            <Box sx={filtroItemStyles}>
              <AppSelect
                appearance="dense"
                fullWidth
                label="Mes"
                value={form.mes === "" ? "" : String(form.mes)}
                onChange={(e) =>
                  patchForm({ mes: e.target.value === "" ? "" : Number(e.target.value) })
                }
                variant="outlined"
                options={BANDEJA_MESES_OPTS_WITH_EMPTY}
              />
            </Box>
            <Box sx={filtroItemStyles}>
              <AppSelect
                appearance="dense"
                fullWidth
                label="Año"
                value={form.anio === "" ? "" : String(form.anio)}
                onChange={(e) =>
                  patchForm({ anio: e.target.value === "" ? "" : Number(e.target.value) })
                }
                variant="outlined"
                options={bandejaYearOptions(defaultMonthYear.anio)}
              />
            </Box>
          </>
        ) : (
          <>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Desde"
                type="date"
                value={form.desde}
                onChange={(e) => patchForm({ desde: e.target.value })}
                InputLabelProps={{ shrink: true }}
                variant="outlined"
              />
            </Box>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Hasta"
                type="date"
                value={form.hasta}
                onChange={(e) => patchForm({ hasta: e.target.value })}
                InputLabelProps={{ shrink: true }}
                variant="outlined"
              />
            </Box>
          </>
        )}
      </Box>

      {validationError && (
        <Typography sx={{ color: "#E53935", fontSize: "0.85rem", mb: 1.5, mt: 1 }}>
          {validationError}
        </Typography>
      )}

      <Box sx={filtroButtonsStyles}>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={handleLimpiar}
          startIcon={<ClearIcon />}
          sx={filtroButtonSecondaryStyles}
        >
          Limpiar
        </AppButton>

        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={handleFiltrar}
          startIcon={<SearchIcon />}
          sx={filtroButtonPrimaryStyles}
        >
          Filtrar
        </AppButton>
      </Box>
    </Box>
  );
};

export default FiltroFechas;
