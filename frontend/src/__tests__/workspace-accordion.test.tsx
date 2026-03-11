import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspaceCard } from "@/components/workspace-card";

it("toggles accordion content and shows current status label", async () => {
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

  expect(screen.getByText("Live")).toBeInTheDocument();
  expect(screen.queryByTestId("members-table")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /mở chatgpt team alpha/i }));
  expect(screen.getByTestId("members-table")).toBeInTheDocument();
});
