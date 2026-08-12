import { useCallback, useRef, useState } from "react";

import { getMapOperativoRealizadosFC, type MapPointFeature } from "../../../api/mapApi";
import {
  mapaRealizadosEmptyMessage,
  mapaRealizadosRubroQueryValue,
  mapaRealizadosTipoQueryValue,
} from "../constants/mapaOperativo";

export type MapaOperativoLoadParams = {
  from: string;
  to: string;
  distritoId: string;
  tipo: string;
  inspectorId: string;
  rubroId?: string;
  rubroLabel?: string;
};

/** Opciones de carga (p. ej. forzar red al pulsar Refrescar). */
export type MapaOperativoLoadOptions = {
  /** Agrega `_` en la query para evitar caché HTTP del GET con los mismos filtros. */
  forceNetwork?: boolean;
};

function debugRealizados(label: string, payload: unknown) {
  if (import.meta.env.DEV) {
    console.debug(`[Mapa Realizados]${label}`, payload);
  }
}

/**
 * Estado y carga del mapa operativo realizados (PR6C.13: sin pendientes legacy).
 */
export function useMapaOperativo() {
  const [features, setFeatures] = useState<MapPointFeature[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const _distritoNum = (distritoId: string): number | undefined => {
    const n = distritoId ? Number(distritoId) : NaN;
    return distritoId && !Number.isNaN(n) ? n : undefined;
  };

  const _inspectorNum = (inspectorId: string): number | undefined => {
    const n = inspectorId ? Number(inspectorId) : NaN;
    return inspectorId && !Number.isNaN(n) ? n : undefined;
  };

  const loadSeqRef = useRef(0);

  const loadRealizados = useCallback(async (p: MapaOperativoLoadParams, opts?: MapaOperativoLoadOptions) => {
    const seq = ++loadSeqRef.current;
    setFeatures([]);
    setInfoMessage(null);
    setLoading(true);
    setError(null);
    try {
      if (!p.from?.trim() || !p.to?.trim()) {
        if (seq !== loadSeqRef.current) return;
        setError("Elegí fecha desde y hasta.");
        setFeatures([]);
        return;
      }
      const queryParams = {
        desde: p.from,
        hasta: p.to,
        distrito_id: _distritoNum(p.distritoId),
        tipo: mapaRealizadosTipoQueryValue(p.tipo),
        inspector_id: _inspectorNum(p.inspectorId),
        rubro_id: mapaRealizadosRubroQueryValue(p.rubroId ?? ""),
        ...(opts?.forceNetwork ? { _: Date.now() } : {}),
      };
      debugRealizados("[tipo selected]", p.tipo);
      debugRealizados("[rubro selected]", p.rubroId);
      debugRealizados("[query params]", queryParams);
      const fc = await getMapOperativoRealizadosFC(queryParams);
      if (seq !== loadSeqRef.current) return;
      const feats = fc.features ?? [];
      debugRealizados("[response count]", feats.length);
      setFeatures(feats);
      if (feats.length === 0) {
        setInfoMessage(
          mapaRealizadosEmptyMessage({ tipo: p.tipo, rubroLabel: p.rubroLabel })
        );
      }
    } catch (e: unknown) {
      if (seq !== loadSeqRef.current) return;
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? "No se pudieron cargar los realizados operativos.");
      setFeatures([]);
    } finally {
      if (seq === loadSeqRef.current) {
        setLoading(false);
      }
    }
  }, []);

  return {
    features,
    loading,
    error,
    infoMessage,
    setInfoMessage,
    loadRealizados,
    setFeatures,
  };
}
