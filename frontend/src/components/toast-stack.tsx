"use client";

import type { ToastState } from "@/lib/use-dashboard-toasts";

type ToastStackProps = {
  toasts: ToastState[];
  onDismiss: (id: number) => void;
};

export function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast-item toast-${toast.tone}`} role="status">
          <div className="toast-accent" aria-hidden="true">
            {toast.tone === "success" ? "✓" : toast.tone === "error" ? "!" : "i"}
          </div>
          <div className="toast-copy">
            <strong className="toast-title">{toast.title}</strong>
            <span className="toast-message">{toast.message}</span>
          </div>
          <button className="toast-close" onClick={() => onDismiss(toast.id)}>
            ✕
          </button>
          <span className="toast-progress" aria-hidden="true" />
        </div>
      ))}
    </div>
  );
}
