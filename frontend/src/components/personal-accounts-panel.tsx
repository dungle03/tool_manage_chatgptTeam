"use client";

import { useCallback, useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import {
  checkPersonalAccount,
  completePersonalAccountOAuthWithCallbackUrl,
  deletePersonalAccount,
  getPersonalAccounts,
  refreshPersonalAccount,
  resolvePersonalAccountDuplicate,
  startPersonalAccountOAuth,
  startPersonalAccountReconnect,
  syncPersonalAccounts,
} from "@/lib/api";
import type {
  DuplicateDecision,
  PersonalAccount,
  PersonalOAuthResult,
} from "@/types/personal-accounts";

import type { ToastTone } from "@/lib/use-dashboard-toasts";

type PersonalAccountsPanelProps = {
  showToast: (title: string, message: string, tone?: ToastTone, dedupeKey?: string) => void;
  setHeaderActions?: Dispatch<SetStateAction<ReactNode>>;
};

type BusyAction = "check" | "refresh" | "reconnect" | "delete";

type DuplicateState = {
  token: string;
  existing: PersonalAccount | null;
  incomingEmail: string;
};

type OAuthModalState = {
  authUrl: string;
  mode: "add" | "reconnect";
};

const statusCopy: Record<string, { label: string; tone: string; hint: string }> = {
  live: { label: "Live", tone: "live", hint: "Account đang hoạt động" },
  die: { label: "Die", tone: "die", hint: "Check health đang lỗi" },
  need_relogin: { label: "Need re-login", tone: "relogin", hint: "Cần login OAuth lại" },
  refreshing: { label: "Refreshing", tone: "unknown", hint: "Đang refresh token" },
  unknown: { label: "Unknown", tone: "unknown", hint: "Chưa kiểm tra" },
};

function formatDateTime(value: string | null): string {
  if (!value) return "Chưa có";
  const normalizedValue = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value)
    ? value
    : `${value.replace(" ", "T")}Z`;
  const date = new Date(normalizedValue);
  if (Number.isNaN(date.getTime())) return "Không rõ";
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(date);
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Có lỗi không xác định";
}

function getAccountDisplayName(account: PersonalAccount): string {
  return account.name?.trim() || account.email || `Account #${account.id}`;
}

function openOAuthPopup(url: string): void {
  const popup = window.open(url, "chatgpt-personal-oauth", "width=580,height=760,left=120,top=70,popup=yes");
  if (!popup) {
    window.location.href = url;
    return;
  }
  popup.focus();
}

export function PersonalAccountsPanel({ showToast, setHeaderActions = () => undefined }: PersonalAccountsPanelProps) {
  const [accounts, setAccounts] = useState<PersonalAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAccounts, setBusyAccounts] = useState<Record<number, BusyAction | undefined>>({});
  const [startingOAuth, setStartingOAuth] = useState(false);
  const [syncingPlans, setSyncingPlans] = useState(false);
  const [callbackUrl, setCallbackUrl] = useState("");
  const [submittingCallbackUrl, setSubmittingCallbackUrl] = useState(false);
  const [oauthModal, setOauthModal] = useState<OAuthModalState | null>(null);
  const [duplicateState, setDuplicateState] = useState<DuplicateState | null>(null);
  const [duplicateSubmitting, setDuplicateSubmitting] = useState<DuplicateDecision | null>(null);
  const [managedAccount, setManagedAccount] = useState<PersonalAccount | null>(null);

  const loadAccounts = useCallback(async (options?: { silent?: boolean; forceFresh?: boolean }) => {
    try {
      if (!options?.silent) setLoading(true);
      setError(null);
      const data = await getPersonalAccounts({ forceFresh: options?.forceFresh });
      setAccounts(data);
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      showToast("Không thể tải Personal Accounts", message, "error", "personal-load-failed");
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void loadAccounts({ forceFresh: true });
  }, [loadAccounts]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadAccounts({ silent: true, forceFresh: true });
    }, 15_000);
    return () => window.clearInterval(interval);
  }, [loadAccounts]);

  useEffect(() => {
    function handleOAuthMessage(event: MessageEvent) {
      if (event.origin !== "http://localhost:1455") return;
      const type = (event.data as { type?: string } | null)?.type;
      if (type === "personal-oauth-success") {
        setOauthModal(null);
        setCallbackUrl("");
        void loadAccounts({ silent: true, forceFresh: true });
        showToast("OAuth hoàn tất", "Account đã được cập nhật trên dashboard.", "success", "personal-oauth-finished");
      } else if (type === "personal-oauth-error") {
        const message = (event.data as { message?: string } | null)?.message || "OAuth callback thất bại.";
        showToast("OAuth thất bại", message, "error", "personal-oauth-callback-error");
      }
    }
    window.addEventListener("message", handleOAuthMessage);
    return () => window.removeEventListener("message", handleOAuthMessage);
  }, [loadAccounts, showToast]);

  const stats = useMemo(() => {
    const live = accounts.filter((account) => account.status === "live").length;
    const needRelogin = accounts.filter((account) => account.requires_relogin || account.status === "need_relogin").length;
    const die = accounts.filter((account) => account.status === "die").length;

    return { total: accounts.length, live, needRelogin, die };
  }, [accounts]);

  useEffect(() => {
    setHeaderActions(
      <>
        <button
          id="personal-account-sync-plans-btn"
          type="button"
          className="btn btn-ghost"
          onClick={() => void handleSyncPlans()}
          disabled={syncingPlans || loading || accounts.length === 0}
        >
          {syncingPlans ? "Syncing..." : "Sync Plans"}
        </button>
        <button
          id="personal-account-reload-btn"
          type="button"
          className="btn btn-ghost"
          onClick={() => void loadAccounts({ forceFresh: true })}
          disabled={loading}
        >
          Reload
        </button>
        <button
          id="add-personal-account-btn"
          type="button"
          className="btn btn-primary personal-add-btn"
          onClick={() => void handleStartOAuth()}
          disabled={startingOAuth}
        >
          {startingOAuth ? "Đang mở OAuth..." : "+ Add Personal ChatGPT Account"}
        </button>
      </>,
    );
    return () => setHeaderActions(null);
  }, [accounts.length, loadAccounts, loading, setHeaderActions, startingOAuth, syncingPlans]);

  function upsertAccount(account: PersonalAccount | null) {
    if (!account) return;
    setAccounts((current) => current.map((item) => item.id === account.id ? account : item));
  }

  async function handleSyncPlans() {
    setSyncingPlans(true);
    try {
      const result = await syncPersonalAccounts({ limit: 10, force: true });
      const updated = result.results
        .map((item) => item.account)
        .filter((account): account is PersonalAccount => Boolean(account));
      if (updated.length > 0) {
        setAccounts((current) => current.map((item) => updated.find((account) => account.id === item.id) || item));
      }
      showToast(
        "Sync Plans hoàn tất",
        `Đã sync ${result.synced}/${result.selected} account, lỗi ${result.failed}.`,
        result.failed ? "info" : "success",
        "personal-sync-plans-finished",
      );
      await loadAccounts({ silent: true, forceFresh: true });
      window.setTimeout(() => void loadAccounts({ silent: true, forceFresh: true }), 1500);
      window.setTimeout(() => void loadAccounts({ silent: true, forceFresh: true }), 4000);
    } catch (err) {
      showToast("Sync Plans thất bại", getErrorMessage(err), "error", "personal-sync-plans-failed");
    } finally {
      setSyncingPlans(false);
    }
  }

  async function handleStartOAuth() {
    setStartingOAuth(true);
    try {
      const result = await startPersonalAccountOAuth();
      setCallbackUrl("");
      setOauthModal({ authUrl: result.authorization_url, mode: "add" });
      openOAuthPopup(result.authorization_url);
      showToast(
        "Đã mở OAuth",
        "Đang chờ popup xác thực. Nếu popup không tự quay lại, dán callback URL trong hộp kết nối.",
        "info",
      );
      window.setTimeout(() => void loadAccounts({ silent: true, forceFresh: true }), 2500);
    } catch (err) {
      showToast("Không mở được OAuth", getErrorMessage(err), "error");
    } finally {
      setStartingOAuth(false);
    }
  }

  async function handleSubmitCallbackUrl() {
    const trimmed = callbackUrl.trim();
    if (!trimmed) {
      showToast("Thiếu callback URL", "Dán nguyên URL chứa code và state sau khi OAuth redirect.", "error");
      return;
    }

    setSubmittingCallbackUrl(true);
    try {
      const result = await completePersonalAccountOAuthWithCallbackUrl(trimmed);
      if (result.status === "duplicate_detected") {
        setDuplicateState({
          token: result.duplicate_token ?? "",
          existing: result.existing_account,
          incomingEmail: result.new_account?.email ?? "unknown",
        });
        showToast("Phát hiện account trùng", "Chọn cách xử lý account trùng để hoàn tất OAuth.", "info");
        return;
      }

      setCallbackUrl("");
      setOauthModal(null);
      if (result.account) {
        await loadAccounts({ silent: true, forceFresh: true });
      }
      showToast("Đã hoàn tất OAuth", "Callback URL hợp lệ, account đã được lưu vào vault.", "success");
    } catch (err) {
      showToast("Callback URL không hợp lệ", getErrorMessage(err), "error");
    } finally {
      setSubmittingCallbackUrl(false);
    }
  }

  async function runAccountAction(account: PersonalAccount, action: BusyAction) {
    setBusyAccounts((current) => ({ ...current, [account.id]: action }));
    try {
      if (action === "check") {
        const result = await checkPersonalAccount(account.id);
        upsertAccount(result.account);
        showToast("Đã check account", result.message, "success");
      } else if (action === "refresh") {
        const result = await refreshPersonalAccount(account.id);
        upsertAccount(result.account);
        showToast("Đã refresh token", result.message, result.next_action ? "info" : "success");
      } else if (action === "reconnect") {
        const result = await startPersonalAccountReconnect(account.id);
        setCallbackUrl("");
        setOauthModal({ authUrl: result.authorization_url, mode: "reconnect" });
        openOAuthPopup(result.authorization_url);
        showToast("Đã mở re-login", "Hoàn tất OAuth để kết nối lại account này.", "info");
      } else if (action === "delete") {
        const confirmed = window.confirm(`Xóa personal account ${account.email}? Token trong tool sẽ bị vô hiệu hóa.`);
        if (!confirmed) return;
        const result = await deletePersonalAccount(account.id);
        setAccounts((current) => current.filter((item) => item.id !== account.id));
        showToast("Đã xóa account", result.message, "success");
      }
    } catch (err) {
      showToast("Thao tác thất bại", getErrorMessage(err), "error");
    } finally {
      setBusyAccounts((current) => ({ ...current, [account.id]: undefined }));
    }
  }

  async function handleResolveDuplicate(decision: DuplicateDecision) {
    if (!duplicateState) return;
    setDuplicateSubmitting(decision);
    try {
      const result: PersonalOAuthResult = await resolvePersonalAccountDuplicate(
        duplicateState.token,
        decision,
      );
      setDuplicateState(null);
      if (result.account) {
        await loadAccounts({ silent: true, forceFresh: true });
      }
      showToast(
        "Đã xử lý account trùng",
        decision === "cancel" ? "Đã hủy thêm account." : "Danh sách account đã được cập nhật.",
        decision === "cancel" ? "info" : "success",
      );
    } catch (err) {
      showToast("Không xử lý được account trùng", getErrorMessage(err), "error");
    } finally {
      setDuplicateSubmitting(null);
    }
  }

  return (
    <section className="personal-panel" aria-labelledby="personal-accounts-heading">
      <section className="summary-strip" aria-label="Personal account summary">
        <div className="summary-strip-kicker-wrap">
          <span className="summary-strip-kicker">Overview</span>
        </div>
        <div className="stats-grid">
          <PersonalStatCard
            label="Accounts"
            value={stats.total.toString()}
            tone="accent"
            meta="Imported accounts"
            icon={<PersonalStatIcon path="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />}
          />
          <PersonalStatCard
            label="Live"
            value={stats.live.toString()}
            tone="success"
            meta="Active sessions"
            icon={<PersonalStatIcon path="M20 6 9 17l-5-5" />}
          />
          <PersonalStatCard
            label="Die"
            value={stats.die.toString()}
            tone="danger"
            meta="Failed checks"
            icon={<PersonalStatIcon path="M18 6 6 18M6 6l12 12" />}
          />
          <PersonalStatCard
            label="Relogin"
            value={stats.needRelogin.toString()}
            tone="warning"
            meta="Awaiting login"
            icon={<PersonalStatIcon path="M15 3h4a2 2 0 0 1 2 2v4M10 17l5-5-5-5M15 12H3m4 9H5a2 2 0 0 1-2-2v-4" />}
          />
        </div>
      </section>

      {error && (
        <div className="personal-error-panel" role="alert">
          <strong>Không tải được dữ liệu.</strong>
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading-state personal-loading">
          <div className="loading-spinner" />
          <span>Đang tải personal accounts...</span>
        </div>
      ) : accounts.length === 0 ? (
        <div className="empty-state personal-empty-state">
          <div className="empty-icon">◌</div>
          <div className="empty-copy">
            <h3>No personal accounts yet.</h3>
            <p>Add your first Personal ChatGPT account with OAuth để bắt đầu theo dõi trạng thái Live/Die.</p>
          </div>
          <button className="btn btn-primary" onClick={() => void handleStartOAuth()} disabled={startingOAuth}>
            Add first personal account
          </button>
        </div>
      ) : (
        <section className="compact-teams-section personal-accounts-section" aria-labelledby="personal-accounts-list-heading">
          <div className="compact-teams-section-header">
            <div className="compact-teams-heading-block">
              <span id="personal-accounts-list-heading" className="compact-teams-kicker">Account collection</span>
            </div>
            <div className="compact-teams-divider" aria-hidden="true" />
          </div>

          <div className="compact-workspace-grid">
            {accounts.map((account) => (
              <PersonalAccountCard
                key={account.id}
                account={account}
                busyAction={busyAccounts[account.id]}
                onCheck={() => void runAccountAction(account, "check")}
                onRefresh={() => void runAccountAction(account, "refresh")}
                onReconnect={() => void runAccountAction(account, "reconnect")}
                onDelete={() => void runAccountAction(account, "delete")}
                onManage={() => setManagedAccount(account)}
              />
            ))}
          </div>
        </section>
      )}

      {oauthModal && (
        <div className="personal-oauth-overlay" role="dialog" aria-modal="true" aria-labelledby="personal-oauth-modal-title">
          <div className="personal-oauth-modal">
            <div className="personal-oauth-titlebar">
              <div className="personal-oauth-dots" aria-hidden="true"><span /><span /><span /></div>
              <h3 id="personal-oauth-modal-title">Connect OpenAI Codex</h3>
            </div>
            <div className="personal-oauth-waiting">
              <span className="personal-oauth-spinner" aria-hidden="true" />
              <span>Waiting for popup authorization...</span>
            </div>
            <div className="personal-oauth-divider"><span>Or paste callback URL manually</span></div>
            <div className="personal-oauth-field">
              <p>Step 1: Open this URL in your browser</p>
              <div className="personal-oauth-copy-row">
                <input value={oauthModal.authUrl} readOnly aria-label="OAuth authorization URL" />
                <button type="button" className="btn btn-ghost" onClick={() => void navigator.clipboard?.writeText(oauthModal.authUrl)}>Copy</button>
              </div>
            </div>
            <div className="personal-oauth-field">
              <p>Step 2: Paste the callback URL here</p>
              <small>After authorization, copy the full localhost URL from your browser if auto-callback did not finish.</small>
              <textarea
                id="personal-callback-url-input"
                value={callbackUrl}
                onChange={(event) => setCallbackUrl(event.target.value)}
                placeholder="http://localhost:1455/auth/callback?code=...&state=..."
                rows={2}
                spellCheck={false}
              />
            </div>
            <div className="personal-oauth-actions">
              <button id="personal-callback-submit-btn" type="button" className="btn btn-secondary" onClick={() => void handleSubmitCallbackUrl()} disabled={submittingCallbackUrl || !callbackUrl.trim()}>
                {submittingCallbackUrl ? "Connecting..." : "Connect"}
              </button>
              <button id="personal-callback-clear-btn" type="button" className="btn btn-ghost" onClick={() => { setOauthModal(null); setCallbackUrl(""); }} disabled={submittingCallbackUrl}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {duplicateState && (
        <PersonalAccountDuplicateModal
          state={duplicateState}
          submitting={duplicateSubmitting}
          onResolve={handleResolveDuplicate}
          onClose={() => setDuplicateState(null)}
        />
      )}

      {managedAccount && (
        <PersonalAccountManageModal
          account={accounts.find((item) => item.id === managedAccount.id) ?? managedAccount}
          busyAction={busyAccounts[managedAccount.id]}
          onCheck={() => void runAccountAction(managedAccount, "check")}
          onRefresh={() => void runAccountAction(managedAccount, "refresh")}
          onReconnect={() => void runAccountAction(managedAccount, "reconnect")}
          onDelete={() => void runAccountAction(managedAccount, "delete")}
          onClose={() => setManagedAccount(null)}
        />
      )}
    </section>
  );
}

function PersonalStatIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="stat-icon-svg" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

function PersonalStatCard({ label, value, tone, meta, icon }: { label: string; value: string; tone: string; meta: string; icon: ReactNode }) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <div className="stat-topline">
        <span className="stat-icon" aria-hidden="true">{icon}</span>
        <div className="stat-copy">
          <span className="stat-label">{label}</span>
          <span className="stat-meta">{meta}</span>
        </div>
      </div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function PersonalAccountCard({
  account,
  busyAction,
  onCheck,
  onRefresh,
  onReconnect,
  onDelete,
  onManage,
}: {
  account: PersonalAccount;
  busyAction?: BusyAction;
  onCheck: () => void;
  onRefresh: () => void;
  onReconnect: () => void;
  onDelete: () => void;
  onManage: () => void;
}) {
  const status = statusCopy[account.status] ?? statusCopy.unknown;
  const isBusy = Boolean(busyAction);
  const compactStatus = status.tone === "live" ? "synced" : status.tone === "relogin" ? "warning" : status.tone === "die" ? "error" : "warning";

  return (
    <article className={`compact-workspace-card personal-compact-card compact-card-${compactStatus}`}>
      <div className="compact-card-toolbar">
        <button
          type="button"
          className={`compact-status personal-compact-status personal-status-${status.tone}`}
          onClick={onCheck}
          disabled={isBusy}
          title={status.hint}
        >
          {busyAction === "check" ? "CHECK" : status.label.toUpperCase()}
        </button>

        <div className="compact-toolbar-actions">
          <button type="button" className="compact-toolbar-icon" onClick={onCheck} disabled={isBusy} aria-label={`Check ${account.email}`}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M16.5 10a6.5 6.5 0 1 1-1.9-4.6" />
              <path d="M13.5 3.5h3v3" />
            </svg>
          </button>
          <button type="button" className="compact-toolbar-icon" onClick={onRefresh} disabled={isBusy} aria-label={`Refresh token ${account.email}`}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ color: "#f5c451" }}>
              <circle cx="7.2" cy="10" r="2.7" />
              <path d="M9.9 10h6.35" />
              <path d="M13.2 10v2.2" />
              <path d="M15.55 10v1.55" />
            </svg>
          </button>
          <button type="button" className="compact-toolbar-icon" onClick={onReconnect} disabled={isBusy} aria-label={`Reconnect ${account.email}`}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12.5 4h3a1.5 1.5 0 0 1 1.5 1.5V8" />
              <path d="M8 14l4-4-4-4" />
              <path d="M12 10H3.5" />
              <path d="M6.5 16H5a1.5 1.5 0 0 1-1.5-1.5V12" />
            </svg>
          </button>
          <button type="button" className="compact-toolbar-icon compact-toolbar-icon-danger" onClick={onDelete} disabled={isBusy} aria-label={`Delete ${account.email}`}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4.5 6h11" />
              <path d="M8 3.5h4" />
              <path d="M6.5 6l.5 9a1 1 0 0 0 1 .94h3.98a1 1 0 0 0 1-.94l.52-9" />
              <path d="M8.5 9.5v3.5" />
              <path d="M11.5 9.5v3.5" />
            </svg>
          </button>
        </div>
      </div>

      <div className="compact-title-stack personal-compact-title-stack">
        <h3 className="compact-workspace-title">{getAccountDisplayName(account)}</h3>
        <p className="personal-compact-email" title={account.email}>{account.email}</p>
      </div>

      <div className="compact-info-list">
        <PersonalCompactRow label="Plan" value={account.plan_type || "unknown"} />
      </div>

      <div className="compact-card-divider" />

      <PersonalCompactTokenRow label="Plus renews" value={formatDateTime(account.plan_renews_at || account.plan_expires_at)} icon="calendar" tone="neutral" />
      <PersonalCompactTokenRow label="Token expires" value={formatDateTime(account.token_expires_at)} icon="token" tone="success" />
      <PersonalCompactTokenRow label="Last checked" value={formatDateTime(account.last_checked_at)} icon="calendar" tone="neutral" />

      {account.last_error_message ? (
        <div className="personal-compact-error" title={account.last_error_message}>
          {account.last_error_code ?? "error"}: {account.last_error_message}
        </div>
      ) : null}

      <div className="compact-card-actions">
        <button type="button" className="btn compact-manage-btn" onClick={onManage}>
          <span>Manage Account</span>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M7 5l5 5-5 5" />
          </svg>
        </button>
      </div>
    </article>
  );
}

function PersonalCompactRow({ label, value }: { label: string; value: string }) {
  const iconPath = "M4.5 6.5h11M6.5 3.5h7a2 2 0 0 1 2 2v11l-5.5-3-5.5 3v-11a2 2 0 0 1 2-2Z";

  return (
    <div className="compact-info-row personal-compact-row">
      <span className="compact-info-label">
        <span className="compact-info-symbol">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d={iconPath} />
          </svg>
        </span>
        <span>{label}</span>
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function PersonalCompactTokenRow({ label, value, icon, tone }: { label: string; value: string; icon: "token" | "calendar"; tone: "success" | "neutral" }) {
  const iconPath = icon === "token"
    ? "M7.5 10a2.5 2.5 0 1 1 4.3 1.77l-4.08 4.08a2.5 2.5 0 1 1-3.54-3.54l1.6-1.6M12.5 10a2.5 2.5 0 1 1-4.3-1.77l4.08-4.08a2.5 2.5 0 1 1 3.54 3.54l-1.6 1.6"
    : "M3.5 5.5h13M6.5 3.5v4M13.5 3.5v4M5.5 5.5h9a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-9a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Z";

  return (
    <div className={`compact-token-row compact-token-row-${tone} personal-token-row`}>
      <span className="compact-token-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d={iconPath} />
        </svg>
      </span>
      <span className="compact-token-copy">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PersonalAccountManageModal({
  account,
  busyAction,
  onCheck,
  onRefresh,
  onReconnect,
  onDelete,
  onClose,
}: {
  account: PersonalAccount;
  busyAction?: BusyAction;
  onCheck: () => void;
  onRefresh: () => void;
  onReconnect: () => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const status = statusCopy[account.status] ?? statusCopy.unknown;
  const isBusy = Boolean(busyAction);

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="personal-manage-title" onClick={onClose}>
      <div className="confirm-dialog personal-manage-dialog" onClick={(event) => event.stopPropagation()}>
        <div className="personal-manage-header">
          <div>
            <h4 id="personal-manage-title">{getAccountDisplayName(account)}</h4>
            <p>{account.email}</p>
          </div>
          <span className={`personal-status-badge personal-status-${status.tone}`}>{status.label}</span>
        </div>

        <div className="personal-manage-grid">
          <PersonalMeta label="Plan" value={account.plan_type || "unknown"} />
          <PersonalMeta label="Subscription" value={account.subscription_plan || "unknown"} />
          <PersonalMeta label="Plus renews" value={formatDateTime(account.plan_renews_at)} />
          <PersonalMeta label="Plus expires" value={formatDateTime(account.plan_expires_at)} />
          <PersonalMeta label="Last plan sync" value={formatDateTime(account.last_plan_sync_at)} />
          <PersonalMeta label="Next plan sync" value={formatDateTime(account.next_plan_sync_at)} />
          <PersonalMeta label="Plan sync error" value={account.plan_sync_error || "None"} />
          <PersonalMeta label="OAuth" value={account.oauth_connected ? "Connected" : "Disconnected"} />
          <PersonalMeta label="Last checked" value={formatDateTime(account.last_checked_at)} />
          <PersonalMeta label="Last refreshed" value={formatDateTime(account.last_refreshed_at)} />
          <PersonalMeta label="Next refresh" value={formatDateTime(account.next_refresh_at)} />
          <PersonalMeta label="Token expires" value={formatDateTime(account.token_expires_at)} />
        </div>

        {account.last_error_message ? (
          <div className="personal-card-error">
            <strong>{account.last_error_code ?? "error"}</strong>
            <span>{account.last_error_message}</span>
          </div>
        ) : null}

        <div className="personal-manage-actions">
          <button type="button" className="btn btn-ghost" onClick={onCheck} disabled={isBusy}>{busyAction === "check" ? "Checking..." : "Check Now"}</button>
          <button type="button" className="btn btn-ghost" onClick={onRefresh} disabled={isBusy}>{busyAction === "refresh" ? "Refreshing..." : "Refresh Token"}</button>
          <button type="button" className="btn btn-secondary" onClick={onReconnect} disabled={isBusy}>{busyAction === "reconnect" ? "Opening..." : "Reconnect OAuth"}</button>
          <button type="button" className="btn btn-danger" onClick={onDelete} disabled={isBusy}>{busyAction === "delete" ? "Deleting..." : "Delete"}</button>
        </div>

        <div className="confirm-actions">
          <button type="button" className="btn btn-primary" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

function PersonalMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="personal-meta-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PersonalAccountDuplicateModal({
  state,
  submitting,
  onResolve,
  onClose,
}: {
  state: DuplicateState;
  submitting: DuplicateDecision | null;
  onResolve: (decision: DuplicateDecision) => Promise<void>;
  onClose: () => void;
}) {
  const disabled = Boolean(submitting);

  return (
    <div className="dialog-overlay" onClick={() => !disabled && onClose()}>
      <div className="confirm-dialog personal-duplicate-dialog" onClick={(event) => event.stopPropagation()}>
        <h4>Account already exists</h4>
        <p>
          Email <strong>{state.incomingEmail}</strong> đã tồn tại trong tool. Chọn ghi đè account cũ hoặc tạo account mới riêng.
        </p>
        {state.existing && (
          <div className="personal-duplicate-existing">
            <span>Existing account</span>
            <strong>{state.existing.email}</strong>
            <small>Status: {state.existing.status}</small>
          </div>
        )}
        <div className="confirm-actions personal-duplicate-actions">
          <button className="btn btn-ghost" disabled={disabled} onClick={() => void onResolve("cancel")}>
            {submitting === "cancel" ? "Cancelling..." : "Cancel"}
          </button>
          <button className="btn btn-secondary" disabled={disabled} onClick={() => void onResolve("create_new")}>
            {submitting === "create_new" ? "Creating..." : "Create new account"}
          </button>
          <button className="btn btn-primary" disabled={disabled} onClick={() => void onResolve("overwrite_existing")}>
            {submitting === "overwrite_existing" ? "Overwriting..." : "Overwrite existing"}
          </button>
        </div>
      </div>
    </div>
  );
}
