import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { InvitePanel } from "@/components/invite-panel";

it("submits email and role", async () => {
  const user = userEvent.setup();
  const onDone = vi.fn();

  render(<InvitePanel orgId="org_test" onDone={onDone} />);

  await user.type(screen.getByPlaceholderText("name@company.com"), "new@company.com");
  await user.selectOptions(screen.getByRole("combobox"), "admin");
  await user.click(screen.getByRole("button", { name: "Send invite" }));

  expect(screen.getByDisplayValue("new@company.com")).toBeInTheDocument();
});
