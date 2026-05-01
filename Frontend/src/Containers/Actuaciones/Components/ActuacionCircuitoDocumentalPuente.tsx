import { Box, CircularProgress, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  fetchComprobacionDocumental,
  fetchNotificacionProrrogaExpedientes,
  type IComprobacionDocumentalResponse,
  type INotificacionProrrogaExpedientesResponse,
} from "../../../api/actuacionesPendientesApi";
import {
  DOC_MODAL_TEXT,
  docModalActuacionScrollCardShellSx,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalSubheadingInCardSx,
} from "../../../styles/documentalModalTokens";
import { AppButton } from "../../../ui";
import { COLORS } from "../styles/filtroStyles";
import {
  actuacionTieneComprobacionActa,
  actuacionTieneNotificacionActa,
  buildActasComprobacionPuente,
  buildGestionNotificacionPuenteHref,
} from "./actuacionDocumentalPuenteUtils";

function PuenteDocumentalBloque({
  overline,
  resumen,
  children,
}: {
  overline: string;
  resumen?: string;
  children: ReactNode;
}) {
  return (
    <Box sx={docModalActuacionScrollCardShellSx(COLORS.primary)}>
      <Typography component="div" sx={docModalBlockOverlineSx}>
        {overline}
      </Typography>
      {resumen ? (
        <Typography component="div" sx={docModalBlockResumenSx}>
          {resumen}
        </Typography>
      ) : null}
      {children}
    </Box>
  );
}

export type ActuacionCircuitoDocumentalPuenteProps = {
  draft: IActuacionListItem;
  open: boolean;
  /** Ejecutar antes de `navigate` (p. ej. cerrar el diálogo padre). */
  onBeforeNavigate: () => void;
};

function dash(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

function PasoEstado({ ok, texto }: { ok: boolean; texto: string }) {
  return (
    <Typography
      variant="body2"
      component="div"
      sx={{
        color: DOC_MODAL_TEXT,
        fontSize: "0.8125rem",
        lineHeight: 1.5,
        pl: 0.5,
        borderLeft: "3px solid",
        borderColor: ok ? "rgba(76,175,80,0.85)" : "rgba(255,193,7,0.75)",
        py: 0.35,
        mb: 0.75,
      }}
    >
      <Box component="span" sx={{ fontWeight: 700, mr: 0.75 }}>
        {ok ? "✓" : "○"}
      </Box>
      {texto}
    </Typography>
  );
}

/**
 * Puente mínimo desde el detalle de actuación hacia las pantallas documentales existentes,
 * con estado derivado de los GET ya previstos por el backend (sin duplicar reglas de negocio).
 */
export function ActuacionCircuitoDocumentalPuente({ draft, open, onBeforeNavigate }: ActuacionCircuitoDocumentalPuenteProps) {
  const navigate = useNavigate();
  const hayComp = actuacionTieneComprobacionActa(draft);
  const hayNotif = actuacionTieneNotificacionActa(draft);

  const [compDoc, setCompDoc] = useState<IComprobacionDocumentalResponse | null>(null);
  const [compErr, setCompErr] = useState(false);
  const [compLoading, setCompLoading] = useState(false);

  const [notifDoc, setNotifDoc] = useState<INotificacionProrrogaExpedientesResponse | null>(null);
  const [notifErr, setNotifErr] = useState(false);
  const [notifLoading, setNotifLoading] = useState(false);

  useEffect(() => {
    if (!open || !draft.id) return;
    let cancelled = false;

    const run = async () => {
      if (hayComp) {
        setCompLoading(true);
        setCompErr(false);
        try {
          const d = await fetchComprobacionDocumental(draft.id);
          if (!cancelled) {
            setCompDoc(d);
            setCompErr(false);
          }
        } catch {
          if (!cancelled) {
            setCompDoc(null);
            setCompErr(true);
          }
        } finally {
          if (!cancelled) setCompLoading(false);
        }
      } else {
        setCompDoc(null);
        setCompErr(false);
        setCompLoading(false);
      }

      if (hayNotif) {
        setNotifLoading(true);
        setNotifErr(false);
        try {
          const d = await fetchNotificacionProrrogaExpedientes(draft.id);
          if (!cancelled) {
            setNotifDoc(d);
            setNotifErr(false);
          }
        } catch {
          if (!cancelled) {
            setNotifDoc(null);
            setNotifErr(true);
          }
        } finally {
          if (!cancelled) setNotifLoading(false);
        }
      } else {
        setNotifDoc(null);
        setNotifErr(false);
        setNotifLoading(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [open, draft.id, hayComp, hayNotif]);

  const compTarget = useMemo(
    () => buildActasComprobacionPuente(draft.id, compDoc, compErr),
    [draft.id, compDoc, compErr]
  );

  const notifHref = useMemo(() => buildGestionNotificacionPuenteHref(draft.id), [draft.id]);

  const expedienteNotifHecho = draft.notificacion_editable === false;

  const go = useCallback(
    (href: string) => {
      onBeforeNavigate();
      navigate(href);
    },
    [navigate, onBeforeNavigate]
  );

  if (!hayComp && !hayNotif) return null;

  return (
    <PuenteDocumentalBloque overline="Circuito documental" resumen="Seguí el trámite administrativo en las pantallas ya existentes.">
      <Stack spacing={2.25} sx={{ width: "100%" }}>
        {hayComp ? (
          <Box>
            <Typography component="h3" sx={docModalSubheadingInCardSx}>
              Comprobación
            </Typography>
            {compLoading ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
                <CircularProgress size={18} sx={{ color: DOC_MODAL_TEXT }} />
                <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.85 }}>
                  Consultando estado documental…
                </Typography>
              </Box>
            ) : (
              <>
                {compErr ? (
                  <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.88, mt: 1, mb: 1 }}>
                    No se pudo leer el estado documental (¿sin comprobación en servidor?). Podés abrir Actas de
                    comprobación igualmente.
                  </Typography>
                ) : null}
                {!compErr && compDoc ? (
                  <Box sx={{ mt: 1 }}>
                    <PasoEstado ok={!!compDoc.expediente_envio} texto="Expediente de envío" />
                    <PasoEstado ok={!!compDoc.oficio} texto="Oficio" />
                    <PasoEstado ok={!!compDoc.expediente_respuesta} texto="Expediente de respuesta del oficio" />
                  </Box>
                ) : null}
                <Box sx={{ mt: 1.5 }}>
                  <AppButton dsVariant="primary" dsSize="sm" onClick={() => go(compTarget.href)}>
                    {compTarget.label}
                  </AppButton>
                </Box>
              </>
            )}
          </Box>
        ) : null}

        {hayComp && hayNotif ? (
          <Box sx={{ borderTop: "1px solid rgba(255,255,255,0.08)", pt: 2.25 }} />
        ) : null}

        {hayNotif ? (
          <Box>
            <Typography component="h3" sx={docModalSubheadingInCardSx}>
              Notificación
            </Typography>
            {notifLoading ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
                <CircularProgress size={18} sx={{ color: DOC_MODAL_TEXT }} />
                <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.85 }}>
                  Consultando expediente / plazo…
                </Typography>
              </Box>
            ) : (
              <>
                {notifErr ? (
                  <Typography variant="body2" sx={{ color: DOC_MODAL_TEXT, opacity: 0.88, mt: 1, mb: 1 }}>
                    No hay datos de plazo en servidor para esta fila (p. ej. sin notificación vinculada). Si cargaste
                    acta, abrí Gestión de notificación para continuar.
                  </Typography>
                ) : null}
                {!notifErr && notifDoc ? (
                  <Box sx={{ mt: 1 }}>
                    <PasoEstado ok={expedienteNotifHecho} texto="Expediente de notificación (inicial)" />
                    <PasoEstado
                      ok={notifDoc.plazos_otorgados > 0 || (notifDoc.plazo_notificacion?.fecha_vencimiento != null && expedienteNotifHecho)}
                      texto={`Plazo / vencimiento: ${dash(notifDoc.plazo_notificacion?.fecha_vencimiento)} · Prórrogas registradas: ${notifDoc.plazos_otorgados ?? 0}`}
                    />
                  </Box>
                ) : null}
                <Box sx={{ mt: 1.5 }}>
                  <AppButton dsVariant="secondary" dsSize="sm" onClick={() => go(notifHref)}>
                    Ir a Gestión de notificación
                  </AppButton>
                </Box>
              </>
            )}
          </Box>
        ) : null}
      </Stack>
    </PuenteDocumentalBloque>
  );
}
