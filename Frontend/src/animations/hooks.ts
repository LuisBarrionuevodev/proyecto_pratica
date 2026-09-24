/**
 * Hooks para animaciones
 */

import { useState, useCallback } from 'react';

/**
 * Hook para manejar animación de refresh de tabla
 * Retorna estado isRefreshing y función triggerRefresh
 */
export const useTableRefresh = () => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const triggerRefresh = useCallback(() => {
    setIsRefreshing(true);
    // Duración sincronizada con tableRefresh variant (400ms)
    setTimeout(() => {
      setIsRefreshing(false);
    }, 400);
  }, []);

  return { isRefreshing, triggerRefresh };
};
