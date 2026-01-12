export const updateField = <T extends object>(
  data: T[],
  index: number,
  field: keyof T,
  value: string | number
): T[] =>
  data.map((item, i) => (i === index ? { ...item, [field]: value } : item));

export const formatNumber = (value: number) =>
  value.toLocaleString("es-AR", { minimumFractionDigits: 0 });
