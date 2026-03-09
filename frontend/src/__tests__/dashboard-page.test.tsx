import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { DashboardSummary } from "@/components/dashboard-summary";

// Test the DashboardSummary component directly since the page now uses hooks
it("renders workspace summary labels", () => {
  render(
    <DashboardSummary totalTeams={2} totalMembers={5} pendingInvites={1} syncErrors={0} />,
  );
  expect(screen.getByText("Total teams")).toBeInTheDocument();
  expect(screen.getByText("Total members")).toBeInTheDocument();
  expect(screen.getByText("Pending invites")).toBeInTheDocument();
});
