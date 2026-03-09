import type { Member, Workspace, Invite } from "@/types/api";

// Lấy admin token từ env (nếu có), dev mode không cần
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

function authHeaders(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (ADMIN_TOKEN) h["Authorization"] = `Bearer ${ADMIN_TOKEN}`;
  return h;
}

export async function getWorkspaces(): Promise<Workspace[]> {
  const res = await fetch("/api/workspaces", { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getWorkspaceMembers(orgId: string): Promise<Member[]> {
  const res = await fetch(`/api/workspaces/${orgId}/members`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function syncWorkspace(orgId: string) {
  return requestJson(`/api/workspaces/${orgId}/sync`, "GET");
}

export async function importTeam(payload: {
  access_token?: string;
  session_token?: string;
  org_id?: string;
  name?: string;
}) {
  return requestJson("/api/teams/import", "POST", payload);
}

export async function inviteMember(payload: { org_id: string; email: string; role: string }) {
  return requestJson("/api/invite", "POST", payload);
}

export async function kickMember(payload: { org_id: string; member_id: number }) {
  return requestJson("/api/member", "DELETE", payload);
}

export async function listInvites(orgId: string): Promise<Invite[]> {
  return requestJson(`/api/invites?org_id=${orgId}`, "GET");
}

export async function resendInvite(payload: { org_id: string; invite_id: string }) {
  return requestJson("/api/resend-invite", "POST", payload);
}

export async function cancelInvite(payload: { org_id: string; invite_id: string; email?: string }) {
  return requestJson("/api/cancel-invite", "DELETE", payload);
}

async function requestJson(url: string, method: string, body?: unknown) {
  const res = await fetch(url, {
    method,
    headers: authHeaders(),
    body: body !== undefined && method !== "GET" ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    // Cố đọc error message từ backend
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data?.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return res.json();
}
