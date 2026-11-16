-- V1.1-CONTRIBUYENTE-UNICIDAD.1 — consultas de solo lectura (copia / digitaliza_test).
-- No fusionar, no borrar, no UPDATE. Reutiliza el relevamiento .0.

-- 1) Duplicados activos por documento normalizado
SELECT
  REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  COUNT(*) AS n_filas,
  COUNT(DISTINCT documento) AS n_literales,
  GROUP_CONCAT(id ORDER BY id) AS ids
FROM contribuyente
WHERE deleted_at IS NULL
GROUP BY doc_norm
HAVING COUNT(*) > 1
ORDER BY n_filas DESC, doc_norm;

-- 2) Mismo normalizado, distinto formato
SELECT
  REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  documento,
  COUNT(*) AS n
FROM contribuyente
WHERE deleted_at IS NULL
GROUP BY doc_norm, documento
HAVING doc_norm IN (
  SELECT doc_norm FROM (
    SELECT REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm
    FROM contribuyente
    WHERE deleted_at IS NULL
    GROUP BY doc_norm
    HAVING COUNT(*) > 1
  ) d
)
ORDER BY doc_norm, documento;

-- 3) Nombres / razones en el mismo normalizado duplicado
SELECT
  REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  c.id,
  c.documento,
  c.apellido,
  c.nombre,
  c.razon_social
FROM contribuyente c
WHERE c.deleted_at IS NULL
  AND REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') IN (
    SELECT doc_norm FROM (
      SELECT REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm
      FROM contribuyente
      WHERE deleted_at IS NULL
      GROUP BY doc_norm
      HAVING COUNT(*) > 1
    ) d
  )
ORDER BY doc_norm, c.id;
