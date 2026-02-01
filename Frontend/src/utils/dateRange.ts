export const getCurrentMonthRange = (): { desde: string; hasta: string } => {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

  const toIso = (d: Date) => d.toISOString().slice(0, 10);

  return {
    desde: toIso(firstDay),
    hasta: toIso(lastDay),
  };
};
