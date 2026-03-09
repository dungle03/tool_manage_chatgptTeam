import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/page";

it("renders workspace summary labels", async () => {
  render(<DashboardPage />);
  expect(screen.getByText("Total teams")).toBeInTheDocument();
  expect(screen.getByText("Total members")).toBeInTheDocument();
  expect(screen.getByText("Pending invites")).toBeInTheDocument();
});
