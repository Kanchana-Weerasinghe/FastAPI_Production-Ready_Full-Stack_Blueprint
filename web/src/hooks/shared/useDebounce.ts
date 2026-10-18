import { useEffect, useState } from "react";

/**
 * A utility hook that delays updating a value until a specified time has passed.
 * Commonly used for search inputs to prevent excessive API calls.
 *
 * @param value - The value to debounce.
 * @param delay - Time in milliseconds to wait before updating (defaults to 300ms).
 * @returns The debounced value.
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}
