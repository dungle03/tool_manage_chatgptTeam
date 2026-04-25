import type {
  Invite,
  InviteMutationResult,
  Member,
  MemberMutationResult,
  UnauthorizedFinding,
  UnauthorizedFindingMutationResult,
  Workspace,
  WorkspaceDeleteResult,
  WorkspaceEvent,
  WorkspaceImportResult,
  WorkspacePolicyUpdateResult,
  WorkspaceRenameResult,
  WorkspaceSyncResult,
  WorkspaceTokenRefreshResult,
  WorkspaceTokenUpdateResult,
  UnauthorizedMemberMode,
} from "@/types/api";

export type WorkspaceDetails = {
  members: Member[];
  invites: Invite[];
  unauthorized_findings: UnauthorizedFinding[];
};

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

export async function getWorkspaces(options?: {
  forceFresh?: boolean;
}): Promise<Workspace[]> {
  return requestJson("/api/workspaces", "GET", undefined, options);
}

export async function getWorkspaceMembers(
  orgId: string,
  options?: { forceFresh?: boolean },
): Promise<Member[]> {
  return requestJson(
    `/api/workspaces/${orgId}/members`,
    "GET",
    undefined,
    options,
  );
}

export async function getWorkspaceDetails(
  orgId: string,
  options?: { forceFresh?: boolean },
): Promise<WorkspaceDetails> {
  return requestJson(
    `/api/workspaces/${orgId}/details`,
    "GET",
    undefined,
    options,
  );
}

export async function listUnauthorizedFindings(
  orgId: string,
  options?: { forceFresh?: boolean },
): Promise<UnauthorizedFinding[]> {
  return requestJson(
    `/api/workspaces/${orgId}/unauthorized-members`,
    "GET",
    undefined,
    options,
  );
}

export type GlobalUnauthorizedFinding = UnauthorizedFinding & {
  workspace_name: string;
};

export async function listAllUnauthorizedFindings(options?: {
  forceFresh?: boolean;
}): Promise<GlobalUnauthorizedFinding[]> {
  return requestJson("/api/unauthorized-findings", "GET", undefined, options);
}

export async function syncWorkspace(
  orgId: string,
): Promise<WorkspaceSyncResult> {
  return requestJson<WorkspaceSyncResult>(
    `/api/workspaces/${orgId}/sync`,
    "POST",
  );
}

export async function updateWorkspaceUnauthorizedMode(
  orgId: string,
  mode: UnauthorizedMemberMode,
): Promise<WorkspacePolicyUpdateResult> {
  return requestJson<WorkspacePolicyUpdateResult>(
    `/api/workspaces/${orgId}/unauthorized-policy`,
    "PATCH",
    { unauthorized_member_mode: mode },
  );
}

export async function trustUnauthorizedFinding(
  orgId: string,
  findingId: number,
  reason?: string,
): Promise<UnauthorizedFindingMutationResult> {
  return requestJson<UnauthorizedFindingMutationResult>(
    `/api/workspaces/${orgId}/unauthorized-members/${findingId}/trust`,
    "POST",
    { reason },
  );
}

export async function kickUnauthorizedFinding(
  orgId: string,
  findingId: number,
  reason?: string,
): Promise<UnauthorizedFindingMutationResult> {
  return requestJson<UnauthorizedFindingMutationResult>(
    `/api/workspaces/${orgId}/unauthorized-members/${findingId}/kick`,
    "POST",
    { reason },
  );
}

export async function importTeam(payload: {
  access_token?: string;
  org_id?: string;
  name?: string;
}): Promise<WorkspaceImportResult> {
  return requestJson<WorkspaceImportResult>(
    "/api/teams/import",
    "POST",
    payload,
  );
}

export async function inviteMember(payload: {
  org_id: string;
  email: string;
  role?: string;
}): Promise<InviteMutationResult> {
  return requestJson<InviteMutationResult>("/api/invite", "POST", payload);
}

export async function kickMember(payload: {
  org_id: string;
  member_id: number;
}): Promise<MemberMutationResult> {
  return requestJson<MemberMutationResult>("/api/member", "DELETE", payload);
}

export async function listInvites(
  orgId: string,
  options?: { forceFresh?: boolean; refreshRemote?: boolean },
): Promise<Invite[]> {
  const params = new URLSearchParams({ org_id: orgId });
  if (options?.refreshRemote) {
    params.set("refresh_remote", "true");
  }
  return requestJson<Invite[]>(
    `/api/invites?${params.toString()}`,
    "GET",
    undefined,
    options,
  );
}

export async function resendInvite(payload: {
  org_id: string;
  invite_id: string;
  email?: string;
}): Promise<InviteMutationResult> {
  return requestJson<InviteMutationResult>(
    "/api/resend-invite",
    "POST",
    payload,
  );
}

export async function cancelInvite(payload: {
  org_id: string;
  invite_id: string;
  email?: string;
}): Promise<InviteMutationResult> {
  return requestJson<InviteMutationResult>(
    "/api/cancel-invite",
    "DELETE",
    payload,
  );
}

export async function deleteWorkspace(
  orgId: string,
): Promise<WorkspaceDeleteResult> {
  return requestJson<WorkspaceDeleteResult>(
    `/api/workspaces/${orgId}`,
    "DELETE",
  );
}

export async function renameWorkspace(
  orgId: string,
  name: string,
): Promise<WorkspaceRenameResult> {
  return requestJson<WorkspaceRenameResult>(
    `/api/workspaces/${orgId}/name`,
    "PATCH",
    { name },
  );
}

export async function updateWorkspaceToken(
  orgId: string,
  accessToken: string,
): Promise<WorkspaceTokenUpdateResult> {
  return requestJson<WorkspaceTokenUpdateResult>(
    `/api/workspaces/${orgId}/token`,
    "PATCH",
    {
      access_token: accessToken,
    },
  );
}

export async function refreshWorkspaceToken(
  orgId: string,
): Promise<WorkspaceTokenRefreshResult> {
  return requestJson<WorkspaceTokenRefreshResult>(
    `/api/workspaces/${orgId}/refresh-token`,
    "POST",
  );
}

export function invalidateApiCache() {
  invalidateGetCache();
}

export function buildWorkspaceEventsUrl(): string {
  const url = new URL("/api/events/workspaces", window.location.origin);
  if (ADMIN_TOKEN) {
    url.searchParams.set("admin_token", ADMIN_TOKEN);
  }
  return url.toString();
}

export function parseWorkspaceEvent(raw: string): WorkspaceEvent {
  return JSON.parse(raw) as WorkspaceEvent;
}

function invalidateGetCache() {
  getCache.clear();
  inflightGets.clear();
}

async function requestJson<T = unknown>(
  url: string,
  method: string,
  body?: unknown,
  options?: { forceFresh?: boolean },
): Promise<T> {
  const isGet = method === "GET";
  const shouldBypassGetCache = isGet && options?.forceFresh;

  if (isGet && !shouldBypassGetCache) {
    const cached = getCache.get(url);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.data as T;
    }

    const inflight = inflightGets.get(url);
    if (inflight) {
      return inflight as Promise<T>;
    }
  } else if (!isGet) {
    invalidateGetCache();
  }

  const request = (async () => {
    const res = await fetch(url, {
      method,
      headers: authHeaders(),
      body:
        body !== undefined && method !== "GET"
          ? JSON.stringify(body)
          : undefined,
      cache: "no-store",
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        const backendDetail =
          typeof data?.detail === "string" ? data.detail.trim() : "";
        if (backendDetail) {
          detail = backendDetail.startsWith("HTTP ")
            ? backendDetail
            : `HTTP ${res.status}: ${backendDetail}`;
        }
      } catch {
        const fallbackText = (await res.text().catch(() => "")).trim();
        if (fallbackText) {
          detail = `HTTP ${res.status}: ${fallbackText}`;
        }
      }
      throw new Error(detail);
    }

    const data = (await res.json()) as T;
    if (isGet) {
      getCache.set(url, { data, expiresAt: Date.now() + GET_CACHE_TTL_MS });
    }
    return data;
  })();

  if (isGet && !shouldBypassGetCache) {
    inflightGets.set(url, request as Promise<unknown>);
  }

  try {
    return await request;
  } finally {
    if (isGet && !shouldBypassGetCache) {
      inflightGets.delete(url);
    }
  }
}
