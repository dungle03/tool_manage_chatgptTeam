import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { InvitePanel } from "@/components/invite-panel";

it("submits email and role", async () => {
  const user = userEvent.setup();
  const onInvite = vi.fn().mockResolvedValue(undefined);

  render(<InvitePanel onInvite={onInvite} />);

  await user.type(screen.getByPlaceholderText("Email"), "new@company.com");
  await user.selectOptions(screen.getByRole("combobox"), "admin");
  await user.click(screen.getByRole("button", { name: "Send Invite" }));

  expect(onInvite).toHaveBeenCalledWith("new@company.com", "admin");
});
