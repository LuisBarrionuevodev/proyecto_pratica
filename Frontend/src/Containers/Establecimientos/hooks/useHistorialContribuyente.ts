import { useCallback, useState } from "react";
import { isAxiosError } from "axios";

import {
  getHistorialContribuyente,
  type IHistorialContribuyenteMeta,
  type IHistorialContribuyenteRow,
} from "../../../api/historialContribuyenteApi";
import {
  documentoHistorialInputValid,
  MSG_DOCUMENTO_HISTORIAL_VACIO,
} from "../utils/historialContribuyenteDocumento";

export type HistorialContribuyenteBuscarParams = {
  documento: string;
  desde?: string | null;
  hasta?: string | null;
  page?: number;
  limit?: number;
};

export function useHistorialContribuyente() {
  const [rows, setRows] = useState<IHistorialContribuyenteRow[]>([]);
  const [meta, setMeta] = useState<IHistorialContribuyenteMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [lastDocumentoInput, setLastDocumentoInput] = useState("");

  const limpiar = useCallback(() => {
    setRows([]);
    setMeta(null);
    setError(null);
    setValidationError(null);
    setHasSearched(false);
    setLastDocumentoInput("");
  }, []);

  const buscar = useCallback(async (params: HistorialContribuyenteBuscarParams) => {
    setLastDocumentoInput(params.documento);
    if (!documentoHistorialInputValid(params.documento)) {
      setValidationError(MSG_DOCUMENTO_HISTORIAL_VACIO);
      setError(null);
      setHasSearched(false);
      setRows([]);
      setMeta(null);
      return;
    }

    setValidationError(null);
    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const res = await getHistorialContribuyente({
        documento: params.documento,
        desde: params.desde,
        hasta: params.hasta,
        page: params.page ?? 1,
        limit: params.limit ?? 20,
      });
      setRows(res.rows);
      setMeta(res.meta);
    } catch (e: unknown) {
      if (isAxiosError(e)) {
        const status = e.response?.status;
        const detail =
          e.response?.data && typeof e.response.data === "object"
            ? (e.response.data as { detail?: string }).detail
            : null;
        if (status === 400) {
          setError(detail ?? "El documento es requerido o no es válido.");
        } else if (status === 401 || status === 403) {
          setError("Sesión expirada o sin permisos para consultar el historial.");
        } else {
          setError(detail ?? "No se pudo cargar el historial del contribuyente.");
        }
      } else {
        setError("No se pudo cargar el historial del contribuyente.");
      }
      setRows([]);
      setMeta(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    rows,
    meta,
    loading,
    error,
    validationError,
    hasSearched,
    lastDocumentoInput,
    buscar,
    limpiar,
  };
}
