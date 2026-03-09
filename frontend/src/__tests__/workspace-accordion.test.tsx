import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspaceCard } from "@/components/workspace-card";

it("toggles accordion content and shows Vietnamese status", async () => {
  const user = userEvent.setup();
  render(
    <WorkspaceCard
      title="ChatGPT Team Alpha"
      members={4}
      memberLimit={7}
      status="synced"
      expandedContent={<div data-testid="members-table">TABLE</div>}
    />,
  );

  expect(screen.getByText("SỐNG")).toBeInTheDocument();
  expect(screen.queryByTestId("members-table")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /ChatGPT Team Alpha/i }));
  expect(screen.getByTestId("members-table")).toBeInTheDocument();
});
