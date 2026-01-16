# Resolución de Conflictos de Dependencias

## Problema Original

Al ejecutar `npm install` aparecían errores de conflicto de peer dependencies:

1. **Conflicto con `marked`**: 
   - `@glideapps/glide-data-grid@6.0.3` requería `marked@^4.0.10`
   - El proyecto no usa `marked` directamente

2. **Conflicto con React**:
   - `@glideapps/glide-data-grid@6.0.3` declaraba peer dependency de `react@^16.12.0 || 17.x || 18.x`
   - El proyecto usa React 19

## Solución Implementada

Se agregó la sección `overrides` en `package.json`:

```json
"overrides": {
  "marked": "^4.3.0",
  "@glideapps/glide-data-grid": {
    "react": "$react",
    "react-dom": "$react-dom"
  }
}
```

### ¿Qué hace esto?

1. **`"marked": "^4.3.0"`**: Fuerza la versión 4.3.0 de `marked` para todas las dependencias que lo requieran, resolviendo el conflicto con glide-data-grid.

2. **`"@glideapps/glide-data-grid": { "react": "$react", "react-dom": "$react-dom" }`**: 
   - Fuerza a `glide-data-grid` a usar las versiones de React y React-DOM definidas en el proyecto (React 19)
   - El prefijo `$` hace referencia a las versiones declaradas en `dependencies`
   - Esto es seguro porque el código de glide-data-grid sí soporta React 19, solo sus peer dependencies no están actualizadas

## Instalación en Nuevas Máquinas

Con esta configuración, simplemente ejecutar:

```bash
npm install
```

Funcionará sin necesidad de flags adicionales como `--legacy-peer-deps` o `--force`.

## Nota sobre Vulnerabilidades

La instalación reporta "1 high severity vulnerability". Para revisar:

```bash
npm audit
```

Para intentar corregir automáticamente:

```bash
npm audit fix
```

## Referencias

- [npm overrides documentation](https://docs.npmjs.com/cli/v10/configuring-npm/package-json#overrides)
- [Glide Data Grid GitHub](https://github.com/glideapps/glide-data-grid)
