import {
  applyFormErrorsFromApi,
  mapApiErrorsToFormState,
  type ApplyFormErrorsOptions,
  type FormErrorsFromApi,
} from "../../utils/parseApiError";

export type ApplyCrudFormErrorsResult = FormErrorsFromApi;

/**
 * Adaptador CRUD sobre `applyFormErrorsFromApi` (422 por campo + mensaje global).
 */
export function applyCrudFormErrorsFromApi(
  err: unknown,
  options?: ApplyFormErrorsOptions
): ApplyCrudFormErrorsResult {
  return applyFormErrorsFromApi(err, options);
}

/**
 * Adaptador CRUD sobre `mapApiErrorsToFormState` (sin side-effect en setters).
 */
export function mapCrudApiErrorsToFormState(err: unknown, options?: ApplyFormErrorsOptions) {
  return mapApiErrorsToFormState(err, options);
}

export type CrudFormErrorHandlers = {
  setFieldErrors: (errors: Record<string, string>) => void;
  setGlobalError: (message: string | null) => void;
};

/**
 * Aplica errores API al estado del formulario CRUD (campos + resumen global).
 */
export function applyCrudFormErrorsToState(
  err: unknown,
  handlers: CrudFormErrorHandlers,
  options?: ApplyFormErrorsOptions
): ApplyCrudFormErrorsResult {
  return applyFormErrorsFromApi(err, {
    ...options,
    setFieldErrors: handlers.setFieldErrors,
    setGlobalError: handlers.setGlobalError,
  });
}
