"use client";

import { useState } from "react";
import { importTeam, syncWorkspace } from "@/lib/api";
import type { RefreshHint, Workspace } from "@/types/api";

type ImportDialogResult = {
  importedOrgId: string | null;
  updatedRecords: Workspace[];
  refreshHint?: RefreshHint;
};

type ImportDialogProps = {
  onClose: () => void;
  onImported: (result: ImportDialogResult) => void;
};

type Tab = "session" | "access";

export function ImportDialog({ onClose, onImported }: ImportDialogProps) {
  const [tab, setTab] = useState<Tab>("access");
  const [sessionToken, setSessionToken] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"input" | "syncing" | "done">("input");
  const [imported, setImported] = useState<{ org_id: string; name: string }[]>([]);
  const [updatedRecords, setUpdatedRecords] = useState<Workspace[]>([]);
  const [refreshHint, setRefreshHint] = useState<RefreshHint | undefined>(undefined);
  const [syncWarnings, setSyncWarnings] = useState<string[]>([]);

  async function handleImport() {
    const payload =
      tab === "session"
        ? { session_token: sessionToken.trim() }
        : { access_token: accessToken.trim() };

    if (!Object.values(payload).some(Boolean)) {
      setError("Vui lòng nhập token.");
      return;
    }

    setLoading(true);
    setError(null);
    setSyncWarnings([]);

    try {
      const res = await importTeam(payload);
      const importedList: { id: number; org_id: string; name: string }[] =
        res?.imported ?? [];

      if (!importedList.length) {
        setError("Không tìm thấy team ChatGPT nào cho token này.");
        return;
      }

      setImported(importedList);
      setUpdatedRecords(res.updated_records ?? res.updated_record ?? []);
      setRefreshHint(res.refresh_hint);
      setStep("syncing");

      const scheduledWarnings = (res.schedule_warnings ?? []).map((warning) => {
        const matchedWorkspace = importedList.find((ws) => ws.org_id === warning.org_id);
        return `${matchedWorkspace?.name ?? warning.org_id}: ${warning.message}`;
      });

      const syncResults = await Promise.allSettled(
        importedList.map(async (ws) => {
          await syncWorkspace(ws.org_id);
          return ws;
        })
      );

      const syncFailures = syncResults.flatMap((result, index) => {
        if (result.status === "fulfilled") {
          return [];
        }

        const detail = result.reason instanceof Error ? result.reason.message : "Không rõ nguyên nhân";
        return [`${importedList[index]?.name ?? importedList[index]?.org_id ?? `workspace-${index + 1}`}: ${detail}`];
      });

      const nextWarnings = [...scheduledWarnings, ...syncFailures];
      setSyncWarnings(nextWarnings);
      if (nextWarnings.length > 0) {
        setError(
          "Import đã xong nhưng một số workspace chưa sync được ngay. Anh vẫn có thể vào dashboard và sync lại sau."
        );
      }
      setStep("done");
    } catch (err: unknown) {
      const rawMsg = err instanceof Error ? err.message : "Có lỗi xảy ra.";

      let friendlyMsg = rawMsg;
      if (rawMsg.includes("ECONNREFUSED") || rawMsg.includes("fetch") || rawMsg.includes("Failed to fetch")) {
        friendlyMsg = "Không kết nối được tới backend (port 8000). Hãy đảm bảo đã chạy: uvicorn app.main:app --reload";
      } else if (rawMsg.includes("401")) {
        friendlyMsg = "Token không hợp lệ hoặc hết hạn. Hãy lấy token mới từ chatgpt.com.";
      } else if (rawMsg.includes("no team account found")) {
        friendlyMsg = "Token này không có tài khoản ChatGPT Team. Hãy kiểm tra lại token có đúng của tài khoản Team không.";
      } else if (rawMsg.includes("502")) {
        friendlyMsg = "Backend không gọi được ChatGPT API. Token có thể đã hết hạn.";
      }

      setError(friendlyMsg);
    } finally {
      setLoading(false);
    }
  }

  function handleDone() {
    onImported({
      importedOrgId: imported[0]?.org_id ?? null,
      updatedRecords,
      refreshHint,
    });
    onClose();
  }

  return (
    <div className="confirm-overlay" onClick={onClose}>
      <div
        className="import-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Import ChatGPT Team"
      >
        <div className="import-dialog-header">
          <h3>🔑 Import ChatGPT Team</h3>
          <button onClick={onClose} className="import-dialog-close" aria-label="Đóng">✕</button>
        </div>

        {step === "input" && (
          <>
            <div className="import-tab-bar">
              <button
                className={`import-tab${tab === "access" ? " active" : ""}`}
                onClick={() => setTab("access")}
              >
                Access Token
              </button>
              <button
                className={`import-tab${tab === "session" ? " active" : ""}`}
                onClick={() => setTab("session")}
              >
                Session Token
              </button>
            </div>

            {tab === "session" && (
              <div className="import-field-group">
                <label className="form-label">Session Token</label>
                <textarea
                  className="import-textarea"
                  placeholder="Dán __Secure-next-auth.session-token từ cookie chatgpt.com vào đây..."
                  value={sessionToken}
                  onChange={(e) => setSessionToken(e.target.value)}
                  rows={4}
                />
                <p className="import-help">
                  📋 <strong>Cách lấy:</strong> Mở chatgpt.com → F12 → Application → Cookies →
                  sao chép giá trị <code>__Secure-next-auth.session-token</code>
                </p>
              </div>
            )}

            {tab === "access" && (
              <div className="import-field-group">
                <label className="form-label">Access Token (Bearer)</label>
                <textarea
                  className="import-textarea"
                  placeholder="Dán Access Token (Bearer) từ ChatGPT vào đây..."
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  rows={4}
                />
                <p className="import-help">
                  📋 <strong>Cách lấy:</strong> Mở chatgpt.com → F12 → Network → bất kỳ request →
                  xem header <code>Authorization: Bearer ...</code>
                </p>
              </div>
            )}

            {error && (
              <div className="import-error">
                ⚠️ {error}
              </div>
            )}

            <div className="import-actions">
              <button className="btn btn-ghost" onClick={onClose}>
                Hủy
              </button>
              <button
                className="btn btn-primary"
                onClick={handleImport}
                disabled={loading}
              >
                {loading ? "⏳ Đang nhập..." : "✅ Import Team"}
              </button>
            </div>
          </>
        )}

        {step === "syncing" && (
          <div className="import-status">
            <div className="loading-spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
            <p>Đang đồng bộ dữ liệu thành viên...</p>
            <ul className="import-workspace-list">
              {imported.map((ws) => (
                <li key={ws.org_id}>⏳ {ws.name}</li>
              ))}
            </ul>
          </div>
        )}

        {step === "done" && (
          <div className="import-status">
            <div style={{ fontSize: 48 }}>🎉</div>
            <h4>Import thành công!</h4>
            {syncWarnings.length > 0 && (
              <div className="import-error" style={{ marginBottom: 16 }}>
                ⚠️ Một số workspace chưa sync xong ngay:
                <ul className="import-workspace-list">
                  {syncWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
            <ul className="import-workspace-list">
              {imported.map((ws) => (
                <li key={ws.org_id} style={{ color: "var(--success)" }}>✅ {ws.name}</li>
              ))}
            </ul>
            <button className="btn btn-primary" onClick={handleDone} style={{ marginTop: 16 }}>
              Xem workspace
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
