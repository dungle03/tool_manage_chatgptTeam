"use client";

export type DashboardViewMode = "default" | "compact";

type DashboardViewToggleProps = {
  value: DashboardViewMode;
  onChange: (mode: DashboardViewMode) => void;
};

function ViewIcon({ mode }: { mode: DashboardViewMode }) {
  if (mode === "default") {
    return (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="4" width="6" height="5.5" rx="1.2" />
        <rect x="11" y="4" width="6" height="5.5" rx="1.2" />
        <rect x="3" y="11" width="6" height="5.5" rx="1.2" />
        <rect x="11" y="11" width="6" height="5.5" rx="1.2" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="14" height="3.2" rx="1.2" />
      <rect x="3" y="8.4" width="14" height="3.2" rx="1.2" />
      <rect x="3" y="12.8" width="14" height="3.2" rx="1.2" />
    </svg>
  );
}

export function DashboardViewToggle({ value, onChange }: DashboardViewToggleProps) {
  return (
    <div className="dashboard-view-toggle" role="group" aria-label="Chế độ hiển thị dashboard">
      <button
        type="button"
        id="dashboard-view-default"
        className={`dashboard-view-option${value === "default" ? " is-active" : ""}`}
        aria-label="Xem dạng lưới chi tiết"
        aria-pressed={value === "default"}
        onClick={() => onChange("default")}
      >
        <ViewIcon mode="default" />
      </button>
      <button
        type="button"
        id="dashboard-view-compact"
        className={`dashboard-view-option${value === "compact" ? " is-active" : ""}`}
        aria-label="Xem dạng gọn"
        aria-pressed={value === "compact"}
        onClick={() => onChange("compact")}
      >
        <ViewIcon mode="compact" />
      </button>
    </div>
  );
}
