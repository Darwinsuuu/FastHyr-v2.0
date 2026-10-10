"use client";

import { useEffect, useState } from "react";

/** `value`, once it has stopped changing for `delay` ms (search boxes that query the API). */
export function useDebouncedValue<T>(value: T, delay = 250): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}
