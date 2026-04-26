from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple
from uuid import UUID, uuid4
import time


DupKey = Tuple[str, str]  # (orden_trabajo_norm, fecha_iso)


@dataclass
class BatchState:
    created_at: float = field(default_factory=lambda: time.time())
    kind: str = "actuaciones"
    # row_id -> dup_key (para recalcular cuando editan una fila)
    row_keys: Dict[str, DupKey] = field(default_factory=dict)
    # dup_key -> row_id (índice rápido para detectar duplicados)
    key_index: Dict[DupKey, str] = field(default_factory=dict)
    # relevamientos: ubicación -> fecha_iso -> conjunto de row_id (misma fecha+ubicación permitido en N filas)
    relev_row_loc_fecha: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    relev_loc_fechas: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)


class InMemoryBatchStore:
    """
    Store simple:
    - start_batch() -> UUID
    - upsert_row_key(batch_id, row_id, dup_key) -> Optional[row_id_duplicada]
    """

    def __init__(self, ttl_seconds: int = 6 * 60 * 60) -> None:
        self._ttl = ttl_seconds
        self._batches: Dict[UUID, BatchState] = {}

    def start_batch(self, kind: str = "actuaciones") -> UUID:
        batch_id = uuid4()
        self._batches[batch_id] = BatchState(kind=kind)
        return batch_id

    def _purge_if_needed(self) -> None:
        now = time.time()
        to_delete = [bid for bid, st in self._batches.items() if (now - st.created_at) > self._ttl]
        for bid in to_delete:
            del self._batches[bid]

    def get(self, batch_id: UUID) -> BatchState:
        self._purge_if_needed()
        if batch_id not in self._batches:
            # si no existe, lo creamos (opción práctica para dev)
            self._batches[batch_id] = BatchState()
        return self._batches[batch_id]

    def upsert_row_key(self, batch_id: UUID, row_id: str, dup_key: DupKey) -> Optional[str]:
        """
        Guarda/actualiza la dup_key de esa fila.
        Devuelve row_id de la fila duplicada si existe duplicado.
        """
        st = self.get(batch_id)

        # si la fila ya tenía una key, limpiar el índice anterior
        old_key = st.row_keys.get(row_id)
        if old_key is not None:
            # solo borrar si el índice apunta a esta misma fila
            if st.key_index.get(old_key) == row_id:
                del st.key_index[old_key]

        # chequeo duplicado: ¿ya existe esa key y es otra fila?
        other_row = st.key_index.get(dup_key)
        if other_row is not None and other_row != row_id:
            # restaurar old_key en índice si existía
            if old_key is not None:
                st.row_keys[row_id] = old_key
                st.key_index[old_key] = row_id
            return other_row

        # si no duplica, guardamos
        st.row_keys[row_id] = dup_key
        st.key_index[dup_key] = row_id
        return None

    def clear_row_key(self, batch_id: UUID, row_id: str) -> None:
        """
        Elimina la fila del índice de duplicados (cuando queda vacía).
        """
        st = self.get(batch_id)
        if st.kind == "relevamientos":
            self._clear_relevamiento_row(st, row_id)
            return
        old_key = st.row_keys.pop(row_id, None)
        if old_key is None:
            return
        if st.key_index.get(old_key) == row_id:
            del st.key_index[old_key]

    @staticmethod
    def _relev_remove_from_index(st: BatchState, row_id: str, location_key: str, fecha_iso: str) -> None:
        by_f = st.relev_loc_fechas.get(location_key)
        if not by_f:
            return
        s = by_f.get(fecha_iso)
        if not s:
            return
        s.discard(row_id)
        if not s:
            del by_f[fecha_iso]
        if not by_f:
            del st.relev_loc_fechas[location_key]

    @staticmethod
    def _relev_add_to_index(st: BatchState, row_id: str, location_key: str, fecha_iso: str) -> None:
        st.relev_loc_fechas.setdefault(location_key, {}).setdefault(fecha_iso, set()).add(row_id)

    @staticmethod
    def _relev_find_other_fecha_conflict(
        st: BatchState, location_key: str, fecha_iso: str, exclude_row_id: str
    ) -> Optional[str]:
        by_f = st.relev_loc_fechas.get(location_key, {})
        for f2, rset in by_f.items():
            if f2 == fecha_iso:
                continue
            for rid in rset:
                if rid != exclude_row_id:
                    return rid
        return None

    def _clear_relevamiento_row(self, st: BatchState, row_id: str) -> None:
        old = st.relev_row_loc_fecha.pop(row_id, None)
        if old is None:
            return
        oloc, ofecha = old
        self._relev_remove_from_index(st, row_id, oloc, ofecha)

    def upsert_relevamiento_dup(self, batch_id: UUID, row_id: str, location_key: str, fecha_iso: str) -> Optional[str]:
        """
        Regla de duplicado relevamientos en el lote:
        - Misma calle+número (ubicación) con **otra** fecha ya presente → duplicado (devuelve row_id conflictivo).
        - Misma ubicación y misma fecha en varias filas → permitido.
        """
        st = self.get(batch_id)
        old = st.relev_row_loc_fecha.get(row_id)

        if old is not None:
            oloc, ofecha = old
            self._relev_remove_from_index(st, row_id, oloc, ofecha)

        other = self._relev_find_other_fecha_conflict(st, location_key, fecha_iso, row_id)
        if other is not None:
            if old is not None:
                oloc, ofecha = old
                st.relev_row_loc_fecha[row_id] = (oloc, ofecha)
                self._relev_add_to_index(st, row_id, oloc, ofecha)
            return other

        st.relev_row_loc_fecha[row_id] = (location_key, fecha_iso)
        self._relev_add_to_index(st, row_id, location_key, fecha_iso)
        return None
