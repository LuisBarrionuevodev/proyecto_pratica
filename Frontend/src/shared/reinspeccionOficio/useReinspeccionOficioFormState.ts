import { useCallback, useMemo, useState } from "react";

import type { IActuacionListItem } from "../../api/actuacionesListApi";
import {
  resolveCumplimientoUiFromPersisted,
  realizoNuevaInspeccionFromPersisted,
  type ReinspeccionOficioCumplimientoUi,
  type ReinspeccionOficioFormMode,
} from "./resolveReinspeccionOficioFormContext";
import {
  subtipoOficioEsRatificacion,
  subtipoOficioEsVerificar,
  tipoActuacionInicialReinspeccionOficio,
} from "./reinspeccionOficioSubtipo";
import {
  deriveVerificarUiFromEstado,
  resolveVerificarEstadoFromPersisted,
  type VerificarEstadoOperativo,
} from "./verificarEstadoOperativo";

export type ReinspeccionOficioFormState = {
  subtipo: string;
  setSubtipo: (v: string) => void;
  cumplimientoUi: ReinspeccionOficioCumplimientoUi;
  setCumplimientoUi: (v: ReinspeccionOficioCumplimientoUi) => void;
  contraproducencia: string;
  setContraproducencia: (v: string) => void;
  realizoNuevaInspeccion: "" | "si" | "no";
  setRealizoNuevaInspeccion: (v: "" | "si" | "no") => void;
  verificarEstadoOperativo: VerificarEstadoOperativo;
  setVerificarEstadoOperativo: (v: VerificarEstadoOperativo) => void;
  esRatificacion: boolean;
  esVerificar: boolean;
  subtipoReadonly: boolean;
  subtipoPendiente: boolean;
  resetFromRow: (row: IActuacionListItem) => void;
};

export type UseReinspeccionOficioFormStateParams = {
  mode: ReinspeccionOficioFormMode;
  initialRow: IActuacionListItem;
  tipoIniciador?: string | null;
};

/**
 * Estado unificado del formulario de reinspección por oficio (Completar / Editar).
 */
export function useReinspeccionOficioFormState(
  params: UseReinspeccionOficioFormStateParams
): ReinspeccionOficioFormState {
  const { mode, initialRow, tipoIniciador } = params;

  const [subtipo, setSubtipoRaw] = useState(() =>
    tipoActuacionInicialReinspeccionOficio(initialRow.tipo_actuacion) ||
    (initialRow.tipo_actuacion ?? "").trim()
  );
  const [cumplimientoUi, setCumplimientoUi] = useState<ReinspeccionOficioCumplimientoUi>(() =>
    resolveCumplimientoUiFromPersisted(initialRow)
  );
  const [contraproducencia, setContraproducencia] = useState(
    () => (initialRow.contraproducencia ?? "").trim()
  );
  const [realizoNuevaInspeccion, setRealizoNuevaInspeccion] = useState<"" | "si" | "no">(() =>
    realizoNuevaInspeccionFromPersisted(initialRow.realizo_nueva_inspeccion)
  );
  const [verificarEstadoOperativo, setVerificarEstadoOperativoRaw] = useState<VerificarEstadoOperativo>(
    () => {
      const res = resolveVerificarEstadoFromPersisted(initialRow);
      return res === "INCONSISTENTE" ? "" : res;
    }
  );

  const esRatificacion = useMemo(() => subtipoOficioEsRatificacion(subtipo), [subtipo]);
  const esVerificar = useMemo(() => subtipoOficioEsVerificar(subtipo), [subtipo]);
  const subtipoReadonly = false;
  const subtipoPendiente = mode === "completar" && !subtipo.trim();

  const setSubtipo = useCallback((next: string) => {
    setSubtipoRaw(next);
    setCumplimientoUi("");
    setContraproducencia("");
    setRealizoNuevaInspeccion("");
    setVerificarEstadoOperativoRaw("");
  }, []);

  const setVerificarEstadoOperativo = useCallback(
    (next: VerificarEstadoOperativo) => {
      const derived = deriveVerificarUiFromEstado(
        next,
        next === "CONTRAPRODUCENCIA" ? contraproducencia : ""
      );
      setVerificarEstadoOperativoRaw(derived.verificarEstadoOperativo);
      setContraproducencia(derived.contraproducencia);
      setRealizoNuevaInspeccion(derived.realizoNuevaInspeccion);
    },
    [contraproducencia]
  );

  const resetFromRow = useCallback((row: IActuacionListItem) => {
    setSubtipoRaw(
      tipoActuacionInicialReinspeccionOficio(row.tipo_actuacion) || (row.tipo_actuacion ?? "").trim()
    );
    setCumplimientoUi(resolveCumplimientoUiFromPersisted(row));
    setContraproducencia((row.contraproducencia ?? "").trim());
    setRealizoNuevaInspeccion(realizoNuevaInspeccionFromPersisted(row.realizo_nueva_inspeccion));
    const estado = resolveVerificarEstadoFromPersisted(row);
    setVerificarEstadoOperativoRaw(estado === "INCONSISTENTE" ? "" : estado);
  }, []);

  return {
    subtipo,
    setSubtipo,
    cumplimientoUi,
    setCumplimientoUi,
    contraproducencia,
    setContraproducencia,
    realizoNuevaInspeccion,
    setRealizoNuevaInspeccion,
    verificarEstadoOperativo,
    setVerificarEstadoOperativo,
    esRatificacion,
    esVerificar,
    subtipoReadonly,
    subtipoPendiente,
    resetFromRow,
  };
}
