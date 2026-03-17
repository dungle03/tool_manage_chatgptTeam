"use client";

import { useEffect, useMemo, useState } from "react";

type UpdateTokenDialogProps = {
  workspaceName: string;
  workspaceOrgId: string;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (accessToken: string) => Promise<void> | void;
};

function normalizeToken(value: string): string {
  return value.trim();
}

export function UpdateTokenDialog({
  workspaceName,
  workspaceOrgId: _workspaceOrgId,
  submitting,
  error,
  onClose,
  onSubmit,
}: UpdateTokenDialogProps) {
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken("");
  }, [workspaceName]);

  const normalizedToken = useMemo(() => normalizeToken(token), [token]);
  const disabled = submitting || !normalizedToken;

  return (
    <div className="confirm-overlay" onClick={() => !submitting && onClose()}>
      <div className="dialog-shell rename-dialog-shell" onClick={(event) => event.stopPropagation()}>
        <div className="dialog-header">
          <div>
            <p className="dialog-eyebrow">Update token</p>
            <h3 className="dialog-title">Cập nhật access token</h3>
            <p className="dialog-subtitle">
              Dán token mới cho <strong>{workspaceName}</strong>.
            </p>
          </div>
          <button
            type="button"
            className="dialog-close"
            id="update-token-close"
            onClick={onClose}
            disabled={submitting}
            aria-label="Đóng dialog cập nhật token"
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 6l8 8" />
              <path d="M14 6l-8 8" />
            </svg>
          </button>
        </div>

        <div className="dialog-body rename-dialog-body">
          <label className="form-label" htmlFor="update-token-input">
            Access token mới
          </label>
          <textarea
            id="update-token-input"
            className="form-input"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Dán access token vào đây"
            rows={6}
            autoFocus
            spellCheck={false}
          />
          <p className="help-text">
            Token mới sẽ thay thế token hiện tại của workspace này.
          </p>
          {error ? <p className="form-error">{error}</p> : null}

          <div className="rename-dialog-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={submitting}
              id="update-token-cancel"
            >
              Hủy
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onSubmit(normalizedToken)}
              disabled={disabled}
              id="update-token-submit"
            >
              {submitting ? "Đang lưu..." : "Lưu token"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
