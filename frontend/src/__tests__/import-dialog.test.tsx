import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ImportDialog } from "@/components/import-dialog";

const importTeamMock = vi.fn();
const syncWorkspaceMock = vi.fn();

vi.mock("@/lib/api", () => ({
  importTeam: (...args: unknown[]) => importTeamMock(...args),
  syncWorkspace: (...args: unknown[]) => syncWorkspaceMock(...args),
}));

describe("ImportDialog", () => {
  it("runs follow-up sync for imported workspaces and shows scheduling warnings", async () => {
    const user = userEvent.setup();
    const onImported = vi.fn();

    let releaseFirstSync: (() => void) | null = null;
    syncWorkspaceMock.mockImplementation((orgId: string) => {
      if (orgId === "org_1") {
        return new Promise<void>((resolve) => {
          releaseFirstSync = resolve;
        });
      }
      return Promise.resolve({ ok: true, members_synced: 0, invites_synced: 0, last_sync: null });
    });

    importTeamMock.mockResolvedValue({
      imported: [
        { id: 1, org_id: "org_1", name: "Alpha Team" },
        { id: 2, org_id: "org_2", name: "Beta Team" },
      ],
      updated_records: [],
      schedule_warnings: [
        { org_id: "org_2", message: "failed to schedule follow-up sync: queued elsewhere" },
      ],
    });

    render(<ImportDialog onClose={vi.fn()} onImported={onImported} />);

    await user.type(screen.getByPlaceholderText("Dán Access Token (Bearer) từ ChatGPT vào đây..."), "token-123");
    await user.click(screen.getByRole("button", { name: "✅ Import Team" }));

    await waitFor(() => {
      expect(syncWorkspaceMock).toHaveBeenCalledTimes(2);
    });
    expect(syncWorkspaceMock).toHaveBeenCalledWith("org_1");
    expect(syncWorkspaceMock).toHaveBeenCalledWith("org_2");

    releaseFirstSync?.();

    expect(await screen.findByText("Import thành công!")).toBeInTheDocument();
    expect(screen.getByText(/Alpha Team/)).toBeInTheDocument();
    expect(
      screen.getByText(/Beta Team: failed to schedule follow-up sync: queued elsewhere/)
    ).toBeInTheDocument();
  });
});
