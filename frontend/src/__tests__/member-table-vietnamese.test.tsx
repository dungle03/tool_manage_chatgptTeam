import { render, screen } from "@testing-library/react";
import { MemberTable } from "@/components/member-table";

it("renders Vietnamese headers and role icon labels", () => {
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
        },
        {
          id: 2,
          name: "Pending",
          email: "pending@team.com",
          role: "member",
          status: "pending",
          invite_date: "2026-03-09T00:00:00Z",
          remote_id: "u_2",
        },
      ]}
    />,
  );

  expect(screen.getByText("EMAIL")).toBeInTheDocument();
  expect(screen.getByText("TÊN TÀI KHOẢN")).toBeInTheDocument();
  expect(screen.getByText("VAI TRÒ")).toBeInTheDocument();
  expect(screen.getByText("NGÀY MỜI")).toBeInTheDocument();
  expect(screen.getByText("HÀNH ĐỘNG")).toBeInTheDocument();

  expect(screen.getByText("👑 Owner")).toBeInTheDocument();
  expect(screen.getByText("⏳ Pending")).toBeInTheDocument();
});
