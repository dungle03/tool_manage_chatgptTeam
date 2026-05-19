import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PersonalAccountsPanel } from "@/components/personal-accounts-panel";
import * as api from "@/lib/api";
import type { PersonalAccount } from "@/types/personal-accounts";

const baseAccount: PersonalAccount = {
  id: 7,
  provider: "codex",
  auth_type: "oauth",
  email: "personal@example.com",
  name: "Personal User",
  plan_type: "plus",
  status: "live",
  is_active: true,
  token_expires_at: "2026-05-19T05:00:00Z",
  last_checked_at: "2026-05-19T03:00:00Z",
  last_refreshed_at: "2026-05-19T03:10:00Z",
  next_refresh_at: "2026-05-19T04:00:00Z",
  last_error_code: null,
  last_error_message: null,
  oauth_connected: true,
  requires_relogin: false,
  created_at: "2026-05-19T02:00:00Z",
  updated_at: "2026-05-19T03:10:00Z",
};

function renderPanel(showToast = vi.fn()) {
  return {
    showToast,
    ...render(<PersonalAccountsPanel showToast={showToast} />),
  };
}

describe("PersonalAccountsPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "getPersonalAccounts").mockResolvedValue([baseAccount]);
    vi.spyOn(api, "startPersonalAccountOAuth").mockResolvedValue({
      authorization_url: "https://auth.example.test/start",
      state: "state-1",
      expires_in: 300,
    });
    vi.spyOn(api, "completePersonalAccountOAuthWithCallbackUrl").mockResolvedValue({
      status: "success",
      account: baseAccount,
      duplicate_token: null,
      existing_account: null,
      new_account: null,
    });
    vi.spyOn(api, "checkPersonalAccount").mockResolvedValue({
      ok: true,
      message: "Account checked",
      account: { ...baseAccount, last_checked_at: "2026-05-19T03:30:00Z" },
      next_action: null,
    });
    vi.spyOn(api, "refreshPersonalAccount").mockResolvedValue({
      ok: true,
      message: "Account refreshed",
      account: baseAccount,
      next_action: null,
    });
    vi.spyOn(api, "deletePersonalAccount").mockResolvedValue({
      ok: true,
      message: "Account deleted",
      account: { ...baseAccount, status: "deleted", is_active: false },
      next_action: null,
    });
    vi.spyOn(api, "startPersonalAccountReconnect").mockResolvedValue({
      authorization_url: "https://auth.example.test/reconnect",
      state: "state-2",
      expires_in: 300,
    });
    vi.spyOn(api, "resolvePersonalAccountDuplicate").mockResolvedValue({
      status: "success",
      account: baseAccount,
      duplicate_token: null,
      existing_account: null,
      new_account: null,
    });
    vi.spyOn(window, "open").mockReturnValue(null);
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("renders public account data without token fields", async () => {
    renderPanel();

    expect(await screen.findByText("Personal User")).toBeInTheDocument();
    expect(screen.getByText("personal@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("Live").length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toContain("access_token");
    expect(document.body.textContent).not.toContain("refresh_token");
    expect(document.body.textContent).not.toContain("id_token");
  });

  it("calls manual check and updates the card", async () => {
    const { showToast } = renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));

    await waitFor(() => expect(api.checkPersonalAccount).toHaveBeenCalledWith(7));
    expect(showToast).toHaveBeenCalledWith("Đã check account", "Account checked", "success");
  });

  it("opens OAuth when adding or reconnecting account", async () => {
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: /Add Personal ChatGPT Account/i }));
    await waitFor(() => expect(window.open).toHaveBeenCalledWith(
      "https://auth.example.test/start",
      "chatgpt-personal-oauth",
      "width=560,height=760,noopener,noreferrer",
    ));

    fireEvent.click(screen.getByRole("button", { name: "Reconnect" }));
    await waitFor(() => expect(api.startPersonalAccountReconnect).toHaveBeenCalledWith(7));
  });

  it("submits pasted OAuth callback URL", async () => {
    const { showToast } = renderPanel();

    const input = await screen.findByLabelText("Callback URL");
    fireEvent.change(input, {
      target: { value: "http://localhost:8484/callback?code=abc&state=state-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Complete OAuth" }));

    await waitFor(() => expect(api.completePersonalAccountOAuthWithCallbackUrl).toHaveBeenCalledWith(
      "http://localhost:8484/callback?code=abc&state=state-1",
    ));
    expect(showToast).toHaveBeenCalledWith(
      "Đã hoàn tất OAuth",
      "Callback URL hợp lệ, account đã được lưu vào vault.",
      "success",
    );
  });

  it("deletes account after confirmation", async () => {
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(api.deletePersonalAccount).toHaveBeenCalledWith(7));
    await waitFor(() => expect(screen.queryByText("Personal User")).not.toBeInTheDocument());
  });
});
