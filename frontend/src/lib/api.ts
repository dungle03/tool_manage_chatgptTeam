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

export async function inviteMember(payload: { org_id: string; email: string; role: string }) {
  return requestJson("/api/invite", "POST", payload);
}

export async function kickMember(payload: { org_id: string; member_id: number }) {
  return requestJson("/api/member", "DELETE", payload);
}

export async function listInvites(orgId: string) {
  return requestJson(`/api/invites?org_id=${orgId}`, "GET");
}

export async function resendInvite(payload: { org_id: string; invite_id: string }) {
  return requestJson("/api/resend-invite", "POST", payload);
}

export async function cancelInvite(payload: { org_id: string; invite_id: string }) {
  return requestJson("/api/cancel-invite", "DELETE", payload);
}

async function requestJson(url: string, method: string, body?: unknown) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Request failed: ${method} ${url}`);
  return res.json();
}
