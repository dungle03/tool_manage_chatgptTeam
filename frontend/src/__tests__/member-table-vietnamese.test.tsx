import { render, screen } from "@testing-library/react";
import { MemberTable } from "@/components/member-table";

it("renders current headers and role labels", () => {
  render(
    <MemberTable
      members={[
        {
          id: 1,
          name: "Owner Name",
          email: "owner@team.com",
          role: "owner",
          status: "active",
          invite_date: "2026-03-09T00:00:00Z",
          remote_id: "u_1",
          created_at: null,
          picture: null,
        },
        {
          id: 2,
          name: "Pending",
          email: "pending@team.com",
          role: "member",
          status: "pending",
          invite_date: "2026-03-09T00:00:00Z",
          remote_id: "u_2",
          created_at: null,
          picture: null,
        },
      ]}
    />,
  );

  expect(screen.getByText("Member")).toBeInTheDocument();
  expect(screen.getByText("Email")).toBeInTheDocument();
  expect(screen.getByText("Role")).toBeInTheDocument();
  expect(screen.getByText("Action")).toBeInTheDocument();

  expect(screen.getByText("Owner")).toBeInTheDocument();
  expect(screen.getByText("User")).toBeInTheDocument();
});
