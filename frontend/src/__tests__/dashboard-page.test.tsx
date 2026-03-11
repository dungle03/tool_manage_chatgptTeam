import { render, screen } from "@testing-library/react";
import { DashboardSummary } from "@/components/dashboard-summary";

it("renders workspace summary labels", () => {
  render(
    <DashboardSummary totalTeams={2} totalMembers={5} pendingInvites={1} syncErrors={0} />,
  );

  expect(screen.getByText("Teams")).toBeInTheDocument();
  expect(screen.getByText("Members")).toBeInTheDocument();
  expect(screen.getByText("Pending")).toBeInTheDocument();
  expect(screen.getByText("Health")).toBeInTheDocument();
});
