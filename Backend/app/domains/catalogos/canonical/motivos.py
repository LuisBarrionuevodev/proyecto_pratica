"""Motivos de notificación y comprobación aprobados."""

from __future__ import annotations

MOTIVOS_NOTIFICACION_CANONICOS: tuple[str, ...] = (
    "Carnet de Sanidad",
    "Desinfeccion",
    "Refacciones",
)

MOTIVOS_COMPROBACION_CANONICOS: tuple[str, ...] = (
    "Falta de Higiene",
    "Condiciones Edilicias Inadecuadas",
    "No Permite la Inspección",
    "Incumplimiento",
    "Incumplimiento de Notificación",
    "Sin Certificado de Desinfección",
    "Sin Carnet de Sanidad",
    "Sin Certificado de Sanidad",
    "Mercadería Vencida",
    "Productos Sin Rotulación",
)
