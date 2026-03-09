import type { Member, Workspace } from "@/types/api";

export async function getWorkspaces(): Promise<Workspace[]> {
  const res = await fetch("/api/workspaces", { method: "GET" });
  if (!res.ok) throw new Error("Failed to fetch workspaces");
  return res.json();
}

export async function getWorkspaceMembers(orgId: string): Promise<Member[]> {
  const res = await fetch(`/api/workspaces/${orgId}/members`, { method: "GET" });
  if (!res.ok) throw new Error("Failed to fetch members");
  return res.json();
}
