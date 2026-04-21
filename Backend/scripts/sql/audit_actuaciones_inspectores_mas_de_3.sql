-- Inventario: actuaciones con MÁS de 3 inspectores activos (deleted_at IS NULL).
-- Ejecutar contra la misma base que usa el backend.

SELECT
    ai.actuaciones_id AS actuacion_id,
    COUNT(*) AS inspectores_activos
FROM actuaciones_inspector AS ai
WHERE ai.deleted_at IS NULL
GROUP BY ai.actuaciones_id
HAVING COUNT(*) > 3
ORDER BY inspectores_activos DESC, actuacion_id ASC;

-- Resumen agregado (una fila):
-- SELECT COUNT(*) AS actuaciones_con_mas_de_3
-- FROM (
--   SELECT actuaciones_id
--   FROM actuaciones_inspector
--   WHERE deleted_at IS NULL
--   GROUP BY actuaciones_id
--   HAVING COUNT(*) > 3
-- ) AS t;
