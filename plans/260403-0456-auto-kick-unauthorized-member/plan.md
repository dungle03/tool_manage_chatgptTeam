# Plan: Auto-Kick Unauthorized Members
Created: 2026-04-03 04:56 +07:00
Status: 🟡 In Progress

## Overview
Feature này thêm cơ chế **phát hiện và xử lý member lạ** theo đúng policy đã chốt:

- **Local DB trước sync** là nguồn whitelist chính.
- Anh **chỉ dùng tool để add member hợp lệ**.
- Bất kỳ member nào xuất hiện trên upstream nhưng **không có trong local DB trước sync** sẽ bị coi là **unauthorized member**.

Feature không cố gắng tìm “ai là người mời”, cũng **không quan tâm pending invite lạ**. Mục tiêu chỉ là:
- phát hiện member lạ xuất hiện ngoài luồng tool,
- cho phép review rõ ràng,
- và sau đó hỗ trợ auto-kick an toàn.

## Product Goal
Biến local DB thành **cổng kiểm soát thành viên hợp lệ** cho từng workspace, để khi có người lạ xuất hiện ngoài policy thì dashboard phát hiện được ngay và có thể tự kick nếu anh bật strict mode.

## Success Criteria
- Mỗi lần sync, hệ thống luôn snapshot được **local members trước sync**.
- Hệ thống tính được `unauthorized_members = remote_members - local_members_before_sync`.
- Member được add hợp lệ qua tool không bị đánh dấu nhầm là unauthorized.
- Dashboard hiển thị rõ member nào là unauthorized, từ workspace nào, phát hiện lúc nào.
- Có ít nhất 2 mode vận hành:
  - `warn_only`
  - `auto_kick`
- Khi `auto_kick` bật, unauthorized member bị kick và có log lý do rõ ràng.
- Local DB chỉ được update sau khi bước detect/enforce hoàn tất, tránh mất dấu diff.
- Có regression coverage cho các case: member lạ xuất hiện khi tool tắt, member hợp lệ qua tool, race giữa sync và kick.

## Scope
### In scope
- Phát hiện unauthorized member dựa trên diff giữa local-before-sync và remote-after-fetch.
- Cơ chế policy per workspace: off / warn_only / auto_kick.
- Gắn cờ unauthorized trong backend và trả dữ liệu ra dashboard.
- UI hiển thị unauthorized members + action phù hợp.
- Ghi log/audit nội bộ cho detect và kick.
- Test backend cho detection logic và enforcement flow.

### Out of scope
- Không xử lý pending invite lạ.
- Không cố truy ra ai là người mời từ upstream.
- Không hỗ trợ owner/admin add người hợp lệ từ web ngoài tool.
- Không làm bulk governance phức tạp hoặc rule engine đa điều kiện ở phase đầu.

## Core Policy
### Authorized member
Một member được coi là hợp lệ nếu:
1. Đã tồn tại trong local DB **trước lần sync hiện tại**.
2. Hoặc vừa đi qua flow add/invite hợp lệ của tool và đã được local DB ghi nhận đúng cách.

### Unauthorized member
Một member bị coi là unauthorized nếu:
1. Có mặt trong danh sách remote members sau khi fetch upstream.
2. Không tồn tại trong local DB snapshot trước sync.
3. Không thuộc ngoại lệ hợp lệ do tool vừa tạo.

## Working Strategy
- **Không dựa vào payload inviter** từ upstream.
- **Không tin trạng thái sau sync làm baseline mới** trước khi detect.
- Sync pipeline phải đổi thứ tự thành:
  1. chụp local snapshot,
  2. fetch remote,
  3. detect unauthorized,
  4. optional enforce,
  5. mới ghi local DB.
- Ưu tiên rollout an toàn: `warn_only` trước, `auto_kick` sau.
- Mọi action kick tự động phải có reason code rõ ràng để dễ debug.

## User Flow
1. Anh bật policy auto-kick cho một workspace.
2. Tool lưu mode của workspace (`off`, `warn_only`, `auto_kick`).
3. Mỗi lần sync:
   - đọc local members cũ,
   - gọi upstream lấy remote members,
   - tính diff,
   - nếu có member lạ thì tạo unauthorized findings.
4. Nếu mode là `warn_only`:
   - dashboard hiện cảnh báo,
   - chưa kick.
5. Nếu mode là `auto_kick`:
   - backend gọi remove member,
   - log event,
   - trả trạng thái đã xử lý.

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Policy Baseline & Sync Guardrails | ⬜ Pending | 0% |
| 02 | Detection Model & Backend Contracts | ⬜ Pending | 0% |
| 03 | Sync Pipeline Detection Logic | ⬜ Pending | 0% |
| 04 | Enforcement Modes & Kick Execution | ⬜ Pending | 0% |
| 05 | Dashboard Visibility & Controls | ⬜ Pending | 0% |
| 06 | Integration Safety & State Consistency | ⬜ Pending | 0% |
| 07 | Testing, QA & Rollout | ⬜ Pending | 0% |

## Phase Notes
### Phase 01 — Policy Baseline & Sync Guardrails
- Chốt chính thức local DB trước sync là whitelist.
- Xác định chính xác workspace nào được bật policy.
- Chốt behavior khi tool vừa restart hoặc sync job chạy lại.
- Chốt rule ngoại lệ cho member vừa được add hợp lệ qua tool.

### Phase 02 — Detection Model & Backend Contracts
- Định nghĩa model dữ liệu cho unauthorized findings và workspace policy mode.
- Chuẩn hóa response trả ra dashboard cho unauthorized state.
- Chốt field nào là source-of-truth: email, remote_id, role, first_seen_at, detection_reason.

### Phase 03 — Sync Pipeline Detection Logic
- Cấy local snapshot vào đầu sync flow.
- Fetch remote members và tính diff trước khi ghi local.
- Gắn cờ unauthorized findings cho member mới xuất hiện.
- Đảm bảo logic detection idempotent qua nhiều lần sync liên tiếp.

### Phase 04 — Enforcement Modes & Kick Execution
- Implement 3 mode: `off`, `warn_only`, `auto_kick`.
- Với `auto_kick`, backend kick member và lưu result code.
- Xử lý failure cases: remote member không còn tồn tại, upstream reject, token lỗi.
- Giữ history tối thiểu cho các lần auto-kick để dễ audit.

### Phase 05 — Dashboard Visibility & Controls
- Thêm hiển thị unauthorized state trong workspace detail.
- Thêm control bật/tắt policy theo workspace.
- Thêm action thủ công: kick now / trust member / ignore (nếu cần ở phase đầu thì ít nhất có kick now).
- Làm copy/label rõ ràng để user hiểu đây là member ngoài whitelist local.

### Phase 06 — Integration Safety & State Consistency
- Đảm bảo sync event, kick action, manual refresh không ghi đè sai state unauthorized.
- Đảm bảo sau kick thì local DB và summary đồng bộ đúng.
- Xử lý race khi user đang xem dashboard lúc background sync chạy.

### Phase 07 — Testing, QA & Rollout
- Test detection với local-before-sync vs remote-after-fetch.
- Test auto-kick only khi policy bật.
- Test member hợp lệ qua tool không bị false positive.
- Test restart scenario: tool tắt, member lạ vào, bật lại, sync phát hiện đúng.
- Chạy rollout theo thứ tự: off → warn_only → auto_kick.

## Key Risks
- Nếu sync pipeline update DB quá sớm, unauthorized member sẽ bị “nuốt mất dấu”.
- Nếu local DB thiếu member hợp lệ do sync cũ lỗi, feature có thể tạo false positive.
- Nếu auto-kick chạy quá sớm mà chưa có UI review tốt, user khó hiểu vì sao member bị đá.
- Nếu upstream remove member lỗi, state local có thể lệch nếu không log/refresh chuẩn.

## Risk Controls
- Bắt buộc snapshot local trước sync.
- Dùng normalized email khi so sánh (`trim + lowercase`).
- Chỉ auto-kick khi workspace policy bật rõ ràng.
- Log đầy đủ detection reason và kick result.
- Rollout bằng `warn_only` trước để xác minh logic thực tế.

## Decision Rules
- Local DB trước sync là whitelist mặc định.
- Không hỗ trợ “member hợp lệ nhưng add ngoài tool” trong feature này.
- Unauthorized detection luôn xảy ra trước bước persist local sync result.
- Nếu remove thất bại, phải giữ finding lại và hiển thị lỗi rõ.
- Nếu member đã bị trust thủ công, sync sau không được đánh lại unauthorized trừ khi có rule khác rõ ràng.

## Recommended Order
1. `/design` để chốt data model, API contract, UI contract cho policy + unauthorized findings.
2. `/code phase-01` để triển khai guardrails cho sync pipeline.
3. Làm detection backend trước, rồi mới nối dashboard.
4. Bật `warn_only` trước trên 1-2 workspace test.
5. Khi logic ổn mới bật `auto_kick`.

## Quick Commands
- Thiết kế chi tiết: `/design`
- Bắt đầu Phase 01: `/code phase-01`
- Xem bước tiếp: `/next`
- Lưu ngữ cảnh: `/save-brain`

## Notes
Plan này cố tình chọn hướng **đơn giản nhưng cứng rắn**: local DB là whitelist, ai xuất hiện ngoài local DB thì bị coi là unauthorized. Đây là hướng phù hợp nhất với policy vận hành mà anh đã chốt.
