import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemberTable } from "@/components/member-table";

it("shows Kick button and confirmation", async () => {
  const user = userEvent.setup();
  render(
    <MemberTable
      members={[{ id: 1, name: "A", email: "a@x.com", role: "member", status: "active", invite_date: null }]}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Kick" }));
  expect(screen.getByText("Confirm kick member")).toBeInTheDocument();
});
