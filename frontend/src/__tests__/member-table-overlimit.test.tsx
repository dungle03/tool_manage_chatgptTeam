import { render, screen } from "@testing-library/react";
import { MemberTable } from "@/components/member-table";
import type { Member } from "@/types/api";

type MemberOverrides = Partial<Member>;

function makeMember(overrides: MemberOverrides = {}): Member {
  return {
    id: overrides.id ?? 1,
    remote_id: overrides.remote_id ?? `remote-${overrides.id ?? 1}`,
    name: overrides.name ?? `Member ${overrides.id ?? 1}`,
    email: overrides.email ?? `member${overrides.id ?? 1}@team.test`,
    role: overrides.role ?? "member",
    status: overrides.status ?? "active",
    invite_date: overrides.invite_date ?? null,
    created_at: overrides.created_at ?? "2026-03-01T00:00:00Z",
    picture: overrides.picture ?? null,
  };
}

function activeMember(i: number, createdAt: string, remoteId?: string): Member {
  return makeMember({
    id: i,
    remote_id: remoteId ?? `remote-${i.toString().padStart(2, "0")}`,
    created_at: createdAt,
    status: "active",
  });
}

describe("MemberTable over-limit classification", () => {
  it("no highlight when active members <= 7", () => {
    const members = [
      activeMember(1, "2026-03-01T00:00:00Z"),
      activeMember(2, "2026-03-02T00:00:00Z"),
      activeMember(3, "2026-03-03T00:00:00Z"),
      activeMember(4, "2026-03-04T00:00:00Z"),
      activeMember(5, "2026-03-05T00:00:00Z"),
      activeMember(6, "2026-03-06T00:00:00Z"),
      activeMember(7, "2026-03-07T00:00:00Z"),
    ];

    render(<MemberTable members={members} />);

    for (const member of members) {
      expect(screen.getByText(member.email).closest("tr")).not.toHaveClass("member-overlimit-row");
    }
  });

  it("highlights exactly 8th+ oldest active members", () => {
    const members = [
      activeMember(1, "2026-03-01T00:00:00Z"),
      activeMember(2, "2026-03-02T00:00:00Z"),
      activeMember(3, "2026-03-03T00:00:00Z"),
      activeMember(4, "2026-03-04T00:00:00Z"),
      activeMember(5, "2026-03-05T00:00:00Z"),
      activeMember(6, "2026-03-06T00:00:00Z"),
      activeMember(7, "2026-03-07T00:00:00Z"),
      activeMember(8, "2026-03-08T00:00:00Z"),
      activeMember(9, "2026-03-09T00:00:00Z"),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("member8@team.test").closest("tr")).toHaveClass("member-overlimit-row");
    expect(screen.getByText("member9@team.test").closest("tr")).toHaveClass("member-overlimit-row");

    expect(screen.getByText("member1@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
    expect(screen.getByText("member7@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
  });

  it("excludes generic non-active statuses from quota classification", () => {
    const members = [
      activeMember(1, "2026-03-01T00:00:00Z"),
      activeMember(2, "2026-03-02T00:00:00Z"),
      activeMember(3, "2026-03-03T00:00:00Z"),
      activeMember(4, "2026-03-04T00:00:00Z"),
      activeMember(5, "2026-03-05T00:00:00Z"),
      activeMember(6, "2026-03-06T00:00:00Z"),
      activeMember(7, "2026-03-07T00:00:00Z"),
      makeMember({
        id: 8,
        email: "removed@team.test",
        status: "removed",
        created_at: "2026-03-08T00:00:00Z",
      }),
      makeMember({
        id: 9,
        email: "error@team.test",
        status: "error",
        created_at: "2026-03-09T00:00:00Z",
      }),
      activeMember(10, "2026-03-10T00:00:00Z"),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("member10@team.test").closest("tr")).toHaveClass("member-overlimit-row");
    expect(screen.getByText("removed@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
    expect(screen.getByText("error@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
  });

  it("excludes pending members from quota classification", () => {
    const members = [
      activeMember(1, "2026-03-01T00:00:00Z"),
      activeMember(2, "2026-03-02T00:00:00Z"),
      activeMember(3, "2026-03-03T00:00:00Z"),
      activeMember(4, "2026-03-04T00:00:00Z"),
      activeMember(5, "2026-03-05T00:00:00Z"),
      activeMember(6, "2026-03-06T00:00:00Z"),
      activeMember(7, "2026-03-07T00:00:00Z"),
      makeMember({
        id: 8,
        email: "pending@team.test",
        status: "pending",
        created_at: "2026-03-08T00:00:00Z",
      }),
      activeMember(9, "2026-03-09T00:00:00Z"),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("pending@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
    expect(screen.getByText("member9@team.test").closest("tr")).toHaveClass("member-overlimit-row");
  });

  it("excludes unknown-date active members from classification", () => {
    const members = [
      activeMember(1, "2026-03-01T00:00:00Z"),
      activeMember(2, "2026-03-02T00:00:00Z"),
      activeMember(3, "2026-03-03T00:00:00Z"),
      activeMember(4, "2026-03-04T00:00:00Z"),
      activeMember(5, "2026-03-05T00:00:00Z"),
      activeMember(6, "2026-03-06T00:00:00Z"),
      activeMember(7, "2026-03-07T00:00:00Z"),
      makeMember({
        id: 8,
        email: "unknown-date@team.test",
        status: "active",
        created_at: null,
      }),
      activeMember(9, "2026-03-09T00:00:00Z"),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("unknown-date@team.test").closest("tr")).not.toHaveClass("member-overlimit-row");
    expect(screen.getByText("member9@team.test").closest("tr")).toHaveClass("member-overlimit-row");
  });

  it("uses remote_id tie-break when created_at is equal", () => {
    const sameDate = "2026-03-10T00:00:00Z";
    const members = [
      makeMember({ id: 1, remote_id: "u-z", email: "z@x.com", created_at: sameDate }),
      makeMember({ id: 2, remote_id: "u-a", email: "a@x.com", created_at: sameDate }),
      makeMember({ id: 3, remote_id: "u-b", email: "b@x.com", created_at: sameDate }),
      makeMember({ id: 4, remote_id: "u-c", email: "c@x.com", created_at: sameDate }),
      makeMember({ id: 5, remote_id: "u-d", email: "d@x.com", created_at: sameDate }),
      makeMember({ id: 6, remote_id: "u-e", email: "e@x.com", created_at: sameDate }),
      makeMember({ id: 7, remote_id: "u-f", email: "f@x.com", created_at: sameDate }),
      makeMember({ id: 8, remote_id: "u-g", email: "g@x.com", created_at: sameDate }),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("z@x.com").closest("tr")).toHaveClass("member-overlimit-row");
    expect(screen.getByText("g@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  });

  it("uses id tie-break when created_at and remote_id are equal", () => {
    const sameDate = "2026-03-10T00:00:00Z";
    const members = [
      makeMember({ id: 80, remote_id: null, email: "80@x.com", created_at: sameDate }),
      makeMember({ id: 10, remote_id: null, email: "10@x.com", created_at: sameDate }),
      makeMember({ id: 70, remote_id: null, email: "70@x.com", created_at: sameDate }),
      makeMember({ id: 20, remote_id: null, email: "20@x.com", created_at: sameDate }),
      makeMember({ id: 60, remote_id: null, email: "60@x.com", created_at: sameDate }),
      makeMember({ id: 30, remote_id: null, email: "30@x.com", created_at: sameDate }),
      makeMember({ id: 50, remote_id: null, email: "50@x.com", created_at: sameDate }),
      makeMember({ id: 40, remote_id: null, email: "40@x.com", created_at: sameDate }),
    ];

    render(<MemberTable members={members} />);

    expect(screen.getByText("80@x.com").closest("tr")).toHaveClass("member-overlimit-row");
    expect(screen.getByText("40@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  });
});
