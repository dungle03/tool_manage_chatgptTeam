# Plan: Project Optimization Roadmap
Created: 2026-03-12 18:09 +07:00
Last Updated: 2026-03-12 22:21 +07:00
Status: ✅ Near Complete

## Overview
Tối ưu toàn diện dự án ChatGPT Team Manager theo 4 trục:
- Flow đúng trong thực tế
- Dashboard mượt và nhanh
- Dữ liệu chính xác, nhất quán
- Kiến trúc dễ bảo trì, dễ mở rộng

## Product Goal
Biến project từ trạng thái “đã dùng được” thành một tool vận hành nội bộ:
- thao tác không cần đoán
- ít phải F5
- phản hồi nhanh
- dữ liệu đáng tin
- dễ debug khi có case edge

## Success Criteria
- Invite vừa tạo có thể revoke ngay
- Sau action, UI cập nhật đúng mà không cần full refresh
- Dashboard giảm cảm giác khựng/lag khi thao tác liên tục
- API mutation trả về contract nhất quán
- Có regression tests cho các flow quan trọng
- `frontend/src/app/page.tsx` được giảm vai trò điều phối trực tiếp

## Current Snapshot
- ✅ Vitest path issue trên Windows đã được xử lý bằng launcher chạy theo real path
- ✅ Frontend đã consume mutation contract mới cho invite/import/delete/kick/resend/revoke
- ✅ `InvitePanel`, `ImportDialog`, `page.tsx` đã áp dụng targeted update + `refresh_hint`
- ✅ `workspace_sync.py` đã được refactor bớt lặp logic scheduling bằng helper rõ nghĩa hơn
- ✅ Đã bổ sung regression coverage cho contract `invite` / `import` / `kick` và sync-related flows
- ✅ `page.tsx` đã bóc bớt state/mutation logic sang `frontend/src/lib/workspace-state.ts`
- ✅ Frontend tests pass (`10 files`, `22 tests`) và backend tests pass (`36 tests`)
- ✅ Đã hoàn thành một pass UX/performance ngắn cho dashboard: memo hóa `WorkspaceCard` / `InviteList` / `MemberTable`, tối ưu lookup trong member action state, và cleanup feedback timeout ở `InvitePanel`
- ✅ Đã thêm SSE/realtime regression coverage cho frontend helper (`workspace-events`) và backend auth/formatter path, đồng thời cập nhật runbook để debug/verify luồng realtime rõ hơn
- ✅ Đã review diff cuối và dọn file tạm `frontend/vitest.temp.config.ts`
- 🟡 Công việc còn lại chủ yếu là commit/push theo cụm thay đổi và, nếu cần, bổ sung docs deploy/staging

## Tech Stack
- Frontend: Next.js + React + TypeScript
- Backend: FastAPI + SQLAlchemy
- Database: SQLite (local workspace cache)
- Realtime: SSE / EventSource
- Upstream integration: ChatGPT account/invite/member APIs
- Testing: Pytest + frontend test suite hiện có

## Working Strategy
- Refactor có kiểm soát, theo phase nhỏ
- Mỗi phase đều có test criteria riêng
- Ưu tiên flow correctness trước, performance sau, polish sau cùng
- Không refactor sâu nhiều khu vực cùng lúc nếu chưa có regression guard

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Baseline & Guardrails | ✅ Near Complete | 90% |
| 02 | Backend Contract & Use-case Cleanup | ✅ Near Complete | 90% |
| 03 | Sync Engine & Source-of-Truth Rules | ✅ Near Complete | 90% |
| 04 | Frontend State Refactor | ✅ Near Complete | 90% |
| 05 | Dashboard UX & Performance Pass | ✅ Near Complete | 90% |
| 06 | Integration & Regression Hardening | ✅ Near Complete | 90% |
| 07 | Operational Readiness & Documentation | ✅ Near Complete | 80% |

## Phase Notes

### Phase 01 — Baseline & Guardrails
- Đã ổn định lại frontend test stack
- Đã fix lỗi Vitest path `C:` / `D:` trên Windows
- Đã có baseline test flow đáng tin cậy hơn cho cả frontend và backend

### Phase 02 — Backend Contract & Use-case Cleanup
- Contract mutation dùng thực tế với `updated_record`, `updated_summary`, `refresh_hint`
- Invite/member/workspace actions đã trả shape nhất quán hơn
- Regression contract tests đã phủ tốt hơn các endpoint mutation chính

### Phase 03 — Sync Engine & Source-of-Truth Rules
- Đã có follow-up scheduling, hot window, sync priority, refresh policy rõ hơn trước
- Đã refactor phần quyết định follow-up success / baseline / retry thành helper riêng
- Rule hiện tại dễ đọc hơn và an toàn hơn nhờ backend tests vẫn pass sau refactor

### Phase 04 — Frontend State Refactor
- `InvitePanel` và `ImportDialog` đã nối vào contract backend mới
- `page.tsx` đã merge targeted update thay cho blind refresh ở nhiều flow
- Đã tách helper state thuần sang `frontend/src/lib/workspace-state.ts` để giảm orchestration inline

### Phase 05 — Dashboard UX & Performance Pass
- Targeted refresh trước đó đã giúp giảm reload không cần thiết
- Đã hoàn thành một pass tối ưu an toàn ở layer component với `React.memo` cho `WorkspaceCard`, `InviteList`, `MemberTable`
- Đã thay lookup `busyMemberIds.includes(...)` sang `Set` memoized để giảm cost lặp trong bảng member
- Đã polish `InvitePanel` bằng cleanup timeout feedback thành công để tránh side effect âm thầm khi re-render/unmount

### Phase 06 — Integration & Regression Hardening
- Frontend tests đang pass
- Backend contract/sync tests đã được tăng coverage rõ rệt
- Đã bổ sung thêm regression cho realtime helper phía frontend (`workspace-events`) để khóa URL builder, malformed payload handling, và cache invalidation
- Đã bổ sung regression ổn định cho SSE/auth path phía backend bằng verify query-token fallback và heartbeat SSE formatter contract

### Phase 07 — Operational Readiness & Documentation
- Đã có README cập nhật và review dự án mới
- Đã thêm `docs/SYNC_RUNBOOK.md` cho sync/debug workflow
- Runbook hiện đã bổ sung rõ hơn cách verify frontend/backend sau thay đổi realtime/SSE
- Còn có thể bổ sung docs deploy/staging nếu mục tiêu là rollout rộng hơn

## Recommended Order
1. Commit lần lượt các cụm backend, frontend, rồi docs/plan
2. Push toàn bộ thay đổi lên remote
3. Nếu cần handoff/deploy, bổ sung docs staging/production
4. Sau đó có thể chuyển sang plan riêng cho feature mới

## Key Risks
- Upstream API trả dữ liệu thiếu hoặc không ổn định
- Optimistic update che lỗi backend nếu không rollback đúng
- Refactor frontend quá rộng có thể làm phát sinh bug mới
- SSE + refresh + local state dễ chồng chéo nếu không có rule rõ

## Decision Rules
- Mutation phải trả về record thật hoặc summary thật khi có thể
- Không dùng ID placeholder để điều khiển action tiếp theo
- UI local state chỉ là lớp hiển thị tạm, không phải nguồn sự thật cuối cùng
- Nếu chưa chắc dữ liệu đã ổn định, ưu tiên báo trạng thái “đang đồng bộ” hơn là báo thành công tuyệt đối

## Quick Commands
- Bắt đầu Phase 01: `/code phase-01`
- Xem bước tiếp theo: `/next`
- Thiết kế chi tiết hơn: `/design`
- Lưu trạng thái hiện tại: `/save-brain`

## Notes
Plan này tập trung vào tối ưu hệ thống hiện có, không phải thêm tính năng mới. Nếu sau khi ổn định nền tảng mà muốn mở rộng feature, nên tạo plan riêng cho feature mới.

## Immediate Next Actions
1. Commit lần lượt các cụm thay đổi đã review
2. Push toàn bộ thay đổi lên remote
3. Nếu cần handoff/deploy, bổ sung thêm docs staging/production
4. Nếu mọi thứ ổn định, chuyển sang plan riêng cho feature mới
