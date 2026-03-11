import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { InvitePanel } from "@/components/invite-panel";

vi.mock("@/lib/api", () => ({
  inviteMember: vi.fn().mockResolvedValue({ ok: true }),
}));

it("submits email", async () => {
  const user = userEvent.setup();
  const onDone = vi.fn();

  render(<InvitePanel orgId="org_test" onDone={onDone} />);

  await user.type(screen.getByPlaceholderText("name@company.com"), "new@company.com");
  await user.click(screen.getByRole("button", { name: "Send invite" }));

  expect(onDone).toHaveBeenCalledTimes(1);
});
