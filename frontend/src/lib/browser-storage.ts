"use client";

import { useCallback, useSyncExternalStore } from "react";

const LOCAL_STORAGE_EVENT = "study-buddy-local-storage";

export function setStoredString(key: string, value: string) {
  localStorage.setItem(key, value);
  window.dispatchEvent(new CustomEvent(LOCAL_STORAGE_EVENT, { detail: { key } }));
}

export function useStoredString(key: string, serverDefault: string): string {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const onCustomChange = (event: Event) => {
        const changedKey = (event as CustomEvent<{ key?: string }>).detail?.key;
        if (!changedKey || changedKey === key) onStoreChange();
      };
      const onStorageChange = (event: StorageEvent) => {
        if (!event.key || event.key === key) onStoreChange();
      };
      window.addEventListener(LOCAL_STORAGE_EVENT, onCustomChange);
      window.addEventListener("storage", onStorageChange);
      return () => {
        window.removeEventListener(LOCAL_STORAGE_EVENT, onCustomChange);
        window.removeEventListener("storage", onStorageChange);
      };
    },
    [key],
  );
  const getSnapshot = useCallback(
    () => localStorage.getItem(key) ?? serverDefault,
    [key, serverDefault],
  );
  const getServerSnapshot = useCallback(() => serverDefault, [serverDefault]);
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
