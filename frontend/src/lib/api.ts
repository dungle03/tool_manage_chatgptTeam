import type { Member, Workspace, Invite } from "@/types/api";

type ImportedWorkspace = { id: number; org_id: string; name: string };
type ImportTeamResponse = { imported: ImportedWorkspace[] };
type SyncWorkspaceResponse = { ok: boolean; members_synced: number; invites_synced: number; last_sync: string };
type MutationResponse = { ok: boolean; [key: string]: unknown };

// Lấy admin token từ env (nếu có), dev mode không cần
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";
const GET_CACHE_TTL_MS = 3_000;
const getCache = new Map<string, { expiresAt: number; data: unknown }>();
const inflightGets = new Map<string, Promise<unknown>>();

function authHeaders(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (ADMIN_TOKEN) h["Authorization"] = `Bearer ${ADMIN_TOKEN}`;
  return h;
}

export async function getWorkspaces(): Promise<Workspace[]> {
  return requestJson("/api/workspaces", "GET");
}

export async function getWorkspaceMembers(orgId: string): Promise<Member[]> {
  return requestJson(`/api/workspaces/${orgId}/members`, "GET");
}

export async function syncWorkspace(orgId: string): Promise<SyncWorkspaceResponse> {
  return requestJson<SyncWorkspaceResponse>(`/api/workspaces/${orgId}/sync`, "GET");
}

export async function importTeam(payload: {
  access_token?: string;
  session_token?: string;
  org_id?: string;
  name?: string;
}): Promise<ImportTeamResponse> {
  return requestJson<ImportTeamResponse>("/api/teams/import", "POST", payload);
}

export async function inviteMember(payload: { org_id: string; email: string; role: string }): Promise<MutationResponse> {
  return requestJson<MutationResponse>("/api/invite", "POST", payload);
}

export async function kickMember(payload: { org_id: string; member_id: number }): Promise<MutationResponse> {
  return requestJson<MutationResponse>("/api/member", "DELETE", payload);
}

export async function listInvites(orgId: string): Promise<Invite[]> {
  return requestJson<Invite[]>(`/api/invites?org_id=${orgId}`, "GET");
}

export async function resendInvite(payload: { org_id: string; invite_id: string }): Promise<MutationResponse> {
  return requestJson<MutationResponse>("/api/resend-invite", "POST", payload);
}

export async function cancelInvite(payload: { org_id: string; invite_id: string; email?: string }): Promise<MutationResponse> {
  return requestJson<MutationResponse>("/api/cancel-invite", "DELETE", payload);
}

export async function deleteWorkspace(orgId: string): Promise<MutationResponse> {
  return requestJson<MutationResponse>(`/api/workspaces/${orgId}`, "DELETE");
}


function invalidateGetCache() {
  getCache.clear();
  inflightGets.clear();
}

async function requestJson<T = unknown>(url: string, method: string, body?: unknown): Promise<T> {
  const isGet = method === "GET";

  if (isGet) {
    const cached = getCache.get(url);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.data as T;
    }

    const inflight = inflightGets.get(url);
    if (inflight) {
      return inflight as Promise<T>;
    }
  } else {
    invalidateGetCache();
  }

  const request = (async () => {
    const res = await fetch(url, {
      method,
      headers: authHeaders(),
      body: body !== undefined && method !== "GET" ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        detail = data?.detail ?? detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    const data = (await res.json()) as T;
    if (isGet) {
      getCache.set(url, { data, expiresAt: Date.now() + GET_CACHE_TTL_MS });
    }
    return data;
  })();

  if (isGet) {
    inflightGets.set(url, request as Promise<unknown>);
  }

  try {
    return await request;
  } finally {
    if (isGet) {
      inflightGets.delete(url);
    }
  }
}
