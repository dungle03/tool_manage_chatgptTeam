"use client";

import { useState } from "react";
import { importTeam, syncWorkspace } from "@/lib/api";

type ImportDialogProps = {
  onClose: () => void;
  onImported: (orgId: string) => void;
};

type Tab = "session" | "access";

export function ImportDialog({ onClose, onImported }: ImportDialogProps) {
  const [tab, setTab] = useState<Tab>("session");
  const [sessionToken, setSessionToken] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"input" | "syncing" | "done">("input");
  const [imported, setImported] = useState<{ org_id: string; name: string }[]>([]);

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

    try {
      const res = await importTeam(payload);
      const importedList: { id: number; org_id: string; name: string }[] =
        res?.imported ?? [];

      if (!importedList.length) {
        setError("Không tìm thấy team ChatGPT nào cho token này.");
        return;
      }

      setImported(importedList);
      setStep("syncing");

      // Auto-sync each imported workspace
      for (const ws of importedList) {
        try {
          await syncWorkspace(ws.org_id);
        } catch {
          // sync errors are non-fatal
        }
      }

      setStep("done");
    } catch (err: unknown) {
      const rawMsg = err instanceof Error ? err.message : "Có lỗi xảy ra.";

      // Dịch lỗi kỹ thuật sang tiếng thường
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
    if (imported.length > 0) {
      onImported(imported[0].org_id);
    }
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
        {/* Header */}
        <div className="import-dialog-header">
          <h3>🔑 Import ChatGPT Team</h3>
          <button onClick={onClose} className="import-dialog-close" aria-label="Đóng">✕</button>
        </div>

        {step === "input" && (
          <>
            {/* Tab selector */}
            <div className="import-tab-bar">
              <button
                className={`import-tab${tab === "session" ? " active" : ""}`}
                onClick={() => setTab("session")}
              >
                Session Token
              </button>
              <button
                className={`import-tab${tab === "access" ? " active" : ""}`}
                onClick={() => setTab("access")}
              >
                Access Token
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
