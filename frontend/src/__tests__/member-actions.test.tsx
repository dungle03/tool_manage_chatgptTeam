import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MemberTable } from "@/components/member-table";

it("shows Kick button and confirmation", async () => {
  const user = userEvent.setup();
  const onKick = vi.fn().mockResolvedValue(undefined);
  render(
    <MemberTable
      members={[{ id: 1, remote_id: null, name: "A", email: "a@x.com", role: "member", status: "active", invite_date: null, created_at: null, picture: null }]}
      onKick={onKick}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Kick" }));
  expect(screen.getByText("Xác nhận xóa thành viên")).toBeInTheDocument();
});

it("bulk kick targets all removable active non-owner members", async () => {
  const user = userEvent.setup();
  const onKick = vi.fn().mockResolvedValue(undefined);

  render(
    <MemberTable
      members={[
        { id: 1, remote_id: null, name: "Owner", email: "owner@x.com", role: "owner", status: "active", invite_date: null, created_at: "2026-04-01T00:00:00Z", picture: null },
        { id: 2, remote_id: null, name: "User A", email: "a@x.com", role: "member", status: "active", invite_date: null, created_at: "2026-04-02T00:00:00Z", picture: null },
        { id: 3, remote_id: null, name: "User B", email: "b@x.com", role: "admin", status: "active", invite_date: null, created_at: "2026-04-03T00:00:00Z", picture: null },
        { id: 4, remote_id: null, name: "Pending", email: "pending@x.com", role: "member", status: "pending", invite_date: null, created_at: "2026-04-04T00:00:00Z", picture: null },
      ]}
      onKick={onKick}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Kick all (2)" }));
  expect(screen.getByText("Xác nhận kick toàn bộ thành viên")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Kick all members" }));

  await waitFor(() => {
    expect(onKick).toHaveBeenCalledTimes(2);
  });
  expect(onKick).toHaveBeenNthCalledWith(1, 2);
  expect(onKick).toHaveBeenNthCalledWith(2, 3);
});
