import { render, screen } from "@testing-library/react";
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
