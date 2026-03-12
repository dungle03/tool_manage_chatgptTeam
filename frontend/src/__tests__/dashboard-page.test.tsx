import { render, screen } from "@testing-library/react";
import { DashboardSummary } from "@/components/dashboard-summary";

it("renders workspace summary labels", () => {
  render(
    <DashboardSummary
      totalTeams={2}
      totalMembers={5}
      availableSlots={9}
      pendingInvites={1}
    />,
  );

  expect(screen.getByText("Teams")).toBeInTheDocument();
  expect(screen.getByText("Members")).toBeInTheDocument();
  expect(screen.getByText("Available Slots")).toBeInTheDocument();
  expect(screen.getByText("Pending")).toBeInTheDocument();
});
