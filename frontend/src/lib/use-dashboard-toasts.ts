"use client";

import { useCallback, useState } from "react";

export type ToastTone = "success" | "error" | "info";

export type ToastState = {
  id: number;
  title: string;
  message: string;
  tone: ToastTone;
  dedupeKey?: string;
};

export function useDashboardToasts() {
  const [toasts, setToasts] = useState<ToastState[]>([]);

  const showToast = useCallback(
    (
      title: string,
      message: string,
      tone: ToastTone = "info",
      dedupeKey?: string
    ) => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((prev) => {
        if (dedupeKey) {
          const alreadyShown = prev.some((toast) => toast.dedupeKey === dedupeKey);
          if (alreadyShown) {
            return prev;
          }
        }
        return [...prev, { id, title, message, tone, dedupeKey }];
      });
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
      }, 3600);
    },
    []
  );

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return {
    toasts,
    showToast,
    dismissToast,
  };
}
