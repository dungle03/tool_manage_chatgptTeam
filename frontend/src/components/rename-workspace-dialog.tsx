"use client";

import { useEffect, useMemo, useState } from "react";

type RenameWorkspaceDialogProps = {
  workspaceName: string;
  workspaceOrgId: string;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (nextName: string) => Promise<void> | void;
};

function normalizeName(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function RenameWorkspaceDialog({
  workspaceName,
  workspaceOrgId: _workspaceOrgId,
  submitting,
  error,
  onClose,
  onSubmit,
}: RenameWorkspaceDialogProps) {
  const [name, setName] = useState("");

  useEffect(() => {
    setName("");
  }, [workspaceName]);

  const normalizedName = useMemo(() => normalizeName(name), [name]);
  const disabled = submitting || !normalizedName;

  return (
    <div className="confirm-overlay" onClick={() => !submitting && onClose()}>
      <div className="dialog-shell rename-dialog-shell" onClick={(event) => event.stopPropagation()}>
        <div className="dialog-header">
          <div>
            <p className="dialog-eyebrow">Rename workspace</p>
            <h3 className="dialog-title">Đổi tên nhóm</h3>
            <p className="dialog-subtitle">
              Cập nhật tên hiển thị cho <strong>{workspaceName}</strong>.
            </p>
          </div>
          <button
            type="button"
            className="dialog-close"
            id="rename-workspace-close"
            onClick={onClose}
            disabled={submitting}
            aria-label="Đóng dialog đổi tên workspace"
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 6l8 8" />
              <path d="M14 6l-8 8" />
            </svg>
          </button>
        </div>

        <div className="dialog-body rename-dialog-body">
          <label className="form-label" htmlFor="rename-workspace-input">
            Tên mới
          </label>
          <input
            id="rename-workspace-input"
            className="form-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nhập tên mới"
            maxLength={120}
            autoFocus
          />
          <p className="help-text">
            Nhập tên hiển thị mới cho workspace này.
          </p>
          {error ? <p className="form-error">{error}</p> : null}

          <div className="rename-dialog-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={submitting}
              id="rename-workspace-cancel"
            >
              Hủy
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onSubmit(normalizedName)}
              disabled={disabled}
              id="rename-workspace-submit"
            >
              {submitting ? "Đang lưu..." : "Lưu"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
