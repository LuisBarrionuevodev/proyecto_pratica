from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from uuid import UUID, uuid4
import time


DupKey = Tuple[str, str]  # (orden_trabajo_norm, fecha_iso)


@dataclass
class BatchState:
    created_at: float = field(default_factory=lambda: time.time())
    # row_id -> dup_key (para recalcular cuando editan una fila)
    row_keys: Dict[str, DupKey] = field(default_factory=dict)
    # dup_key -> row_id (índice rápido para detectar duplicados)
    key_index: Dict[DupKey, str] = field(default_factory=dict)


class InMemoryBatchStore:
    """
    Store simple:
    - start_batch() -> UUID
    - upsert_row_key(batch_id, row_id, dup_key) -> Optional[row_id_duplicada]
    """

    def __init__(self, ttl_seconds: int = 6 * 60 * 60) -> None:
        self._ttl = ttl_seconds
        self._batches: Dict[UUID, BatchState] = {}

    def start_batch(self) -> UUID:
        batch_id = uuid4()
        self._batches[batch_id] = BatchState()
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
