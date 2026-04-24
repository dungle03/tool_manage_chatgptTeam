export type WorkspaceActionErrorKind =
  | "sync"
  | "kick"
  | "resend"
  | "revoke"
  | "delete_workspace"
  | "rename_workspace";

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return "Lỗi không xác định";
}

export function formatDashboardSyncTime(lastSync?: string | null): string {
  if (!lastSync) return "Chưa sync";
  const diff = Math.floor((Date.now() - new Date(lastSync).getTime()) / 1000);
  if (diff < 60) return `${diff}s trước`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h trước`;
  return `${Math.floor(diff / 86400)}d trước`;
}

export function formatDashboardDateLabel(prefix: string, timestamp?: string | null): string {
  if (!timestamp) return `${prefix}: Chưa rõ`;

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return `${prefix}: Chưa rõ`;
  }

  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const year = date.getUTCFullYear();
  return `${prefix}: ${day}/${month}/${year}`;
}

export function getActionErrorCopy(
  action: WorkspaceActionErrorKind,
  error: unknown
): string {
  const detail = getErrorMessage(error);

  if (detail.includes("HTTP 404")) {
    return "Dữ liệu liên quan không còn tồn tại hoặc dashboard đang hiển thị bản cũ. Hãy tải lại danh sách.";
  }

  if (detail.includes("HTTP 409") || detail.includes("cannot remove owner")) {
    return "Thao tác bị chặn vì dữ liệu hiện tại không cho phép thực hiện bước này.";
  }

  if (detail.includes("HTTP 401") || detail.includes("HTTP 403")) {
    return "Token hiện tại không hợp lệ hoặc đã hết hạn. Hãy kiểm tra lại phiên làm việc rồi thử lại.";
  }

  if (detail.includes("HTTP 500") || detail.includes("HTTP 502")) {
    return `Backend hoặc dịch vụ đồng bộ đang lỗi: ${detail}`;
  }

  const fallbackByAction = {
    sync: "Workspace chưa thể đồng bộ ở thời điểm này.",
    kick: "Chưa thể xóa thành viên ở thời điểm này.",
    resend: "Chưa thể gửi lại lời mời ở thời điểm này.",
    revoke: "Chưa thể thu hồi lời mời ở thời điểm này.",
    delete_workspace: "Chưa thể xóa workspace ở thời điểm này.",
    rename_workspace: "Chưa thể đổi tên workspace ở thời điểm này.",
  } satisfies Record<WorkspaceActionErrorKind, string>;

  return detail === "Lỗi không xác định"
    ? fallbackByAction[action]
    : `${fallbackByAction[action]} Chi tiết: ${detail}`;
}
