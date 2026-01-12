import { useState } from "react";

export function useEditableTable<T extends object>(initialData: T[]) {
  const [data, setData] = useState<T[]>(initialData);

  const handleUpdate = (
    index: number,
    field: keyof T,
    value: string | number
  ) => {
    setData((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      )
    );
  };

  return { data, setData, handleUpdate };
}