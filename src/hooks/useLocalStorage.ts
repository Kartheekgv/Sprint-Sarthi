import { useEffect, useState } from 'react';

/**
 * Small typed localStorage helper. The fallback value is used when storage is
 * unavailable, empty, or contains invalid JSON.
 */
export function useLocalStorage<T>(key: string, fallbackValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const savedValue = window.localStorage.getItem(key);
      return savedValue ? (JSON.parse(savedValue) as T) : fallbackValue;
    } catch {
      return fallbackValue;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // The app remains usable when storage is disabled by the browser.
    }
  }, [key, value]);

  return [value, setValue] as const;
}
