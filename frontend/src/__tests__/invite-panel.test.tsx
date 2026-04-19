import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { InvitePanel } from "@/components/invite-panel";
import { inviteMember } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  inviteMember: vi.fn(),
}));

const inviteMemberMock = vi.mocked(inviteMember);

beforeEach(() => {
  inviteMemberMock.mockReset();
});

it("submits unique emails from multiple lines", async () => {
  inviteMemberMock.mockResolvedValue({ ok: true });
  const user = userEvent.setup();
  const onDone = vi.fn();

  render(<InvitePanel orgId="org_test" onDone={onDone} />);

  await user.type(
    screen.getByLabelText("Danh sách email"),
    "new@company.com\nnew2@company.com\nNEW@company.com"
  );
  await user.click(screen.getByRole("button", { name: "Send invite" }));

  await waitFor(() => {
    expect(inviteMemberMock).toHaveBeenCalledTimes(2);
  });
  expect(inviteMemberMock).toHaveBeenNthCalledWith(1, {
    org_id: "org_test",
    email: "new@company.com",
  });
  expect(inviteMemberMock).toHaveBeenNthCalledWith(2, {
    org_id: "org_test",
    email: "new2@company.com",
  });
  expect(onDone).toHaveBeenCalledTimes(2);
  expect(await screen.findByText("Đã gửi thành công 2 lời mời.")).toBeInTheDocument();
});

it("shows invalid email feedback and does not submit", async () => {
  const user = userEvent.setup();

  render(<InvitePanel orgId="org_test" />);

  await user.type(screen.getByLabelText("Danh sách email"), "valid@company.com\nnot-an-email");
  await user.click(screen.getByRole("button", { name: "Send invite" }));

  expect(inviteMemberMock).not.toHaveBeenCalled();
  expect(await screen.findByText(/Email không hợp lệ:/)).toBeInTheDocument();
});
