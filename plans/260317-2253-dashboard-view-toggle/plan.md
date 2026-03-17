# Plan: Dashboard View Toggle & Real Workspace Rename
Created: 2026-03-17 22:53 +07:00
Status: 🟡 In Progress

## Overview
Feature này thêm **2 chế độ hiển thị dashboard**:
1. **Current View**: giữ nguyên giao diện hiện tại.
2. **Compact View**: hiển thị giống mockup user mong muốn để nhìn được nhiều team hơn, ít phải scroll hơn.

Ngoài ra, feature còn thêm khả năng **đổi tên workspace thật** bằng icon edit cạnh tên team. Frontend sẽ gửi lệnh rename xuống backend, backend gọi upstream API/internal web flow để cập nhật tên workspace thực tế rồi phản hồi lại summary mới cho dashboard.

## Product Goal
Biến dashboard từ “đẹp và dùng được” thành “đẹp + quản lý nhiều team nhanh + thao tác rename thật + vẫn mượt và ổn định”.

## Success Criteria
- Có nút chuyển đổi rõ ràng giữa `Current View` và `Compact View`.
- Compact view hiển thị được nhiều team hơn trên cùng màn hình mà không làm dashboard rối.
- View preference được giữ ổn định trong phiên và nên nhớ lại sau reload.
- Mỗi workspace ở compact view hiển thị được các thông tin quan trọng: tên, slot dùng theo dạng `x/7`, pending, token expiry, status, quick actions.
- Icon edit cạnh tên team mở được flow rename rõ ràng, an toàn.
- Rename thành công sẽ cập nhật **workspace thật** qua API/upstream và dashboard phản ánh đúng ngay sau đó.
- Rename thất bại phải báo lỗi rõ, không làm hỏng state local.
- Không làm chậm dashboard hiện tại, không tăng số lần reload toàn trang vô ích.
- Có regression coverage cho toggle view, rename success, rename failure, và behavior khi sync/event cập nhật song song.

## Scope
### In scope
- Toggle giữa 2 chế độ hiển thị dashboard.
- Compact workspace card/list theo style mockup user chọn.
- State quản lý view mode ở frontend.
- UI rename workspace bằng icon edit + modal/input xác nhận.
- Backend endpoint rename workspace.
- Service layer xác minh/call upstream rename workspace.
- Refresh/update summary đúng sau rename.
- Test và QA checklist cho toàn bộ flow.

### Out of scope
- Thiết kế lại toàn bộ dashboard thành sản phẩm mới hoàn toàn.
- Thêm bulk rename hoặc batch actions.
- Đổi kiến trúc realtime hiện có ngoài những phần cần thiết để feature này an toàn.
- Refactor lớn toàn bộ page nếu chưa cần cho feature.

## Working Strategy
- Giữ `Current View` làm baseline an toàn.
- Thêm `Compact View` theo kiểu mở rộng, không phá flow cũ.
- Tách rename flow thành một vertical slice hoàn chỉnh: UI → backend → upstream → summary update → tests.
- Ưu tiên rollback-safe state updates: local chỉ update khi backend trả summary thật.
- Dùng feature flag nội bộ theo state/component boundary nếu cần để giảm rủi ro rollout.

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Discovery & Guardrails | ⬜ Pending | 0% |
| 02 | UX Contract & Data Mapping | ⬜ Pending | 0% |
| 03 | Backend Rename API | ⬜ Pending | 0% |
| 04 | Frontend View Toggle | ⬜ Pending | 0% |
| 05 | Compact View Implementation | ⬜ Pending | 0% |
| 06 | Integration & State Safety | ⬜ Pending | 0% |
| 07 | Testing & QA Hardening | ⬜ Pending | 0% |

## Phase Notes
### Phase 01 — Discovery & Guardrails
- Xác nhận chính xác component/layout hiện tại dùng để render workspace list.
- Xác nhận endpoint rename thực tế bằng network behavior hoặc upstream pattern đã có.
- Định nghĩa fallback nếu upstream rename không phản hồi như mong đợi.
- Chốt compact view là biến thể của dashboard hiện tại, không phải tách route mới.

### Phase 02 — UX Contract & Data Mapping
- Chốt UI toggle placement, icon, label, active state.
- Chốt shape thông tin hiển thị ở compact view.
- Chốt rename modal/dialog UX: open, validate, submit, loading, success, failure.
- Chốt source-of-truth cho các field được hiển thị trong compact view.

### Phase 03 — Backend Rename API
- Thêm route backend để rename workspace.
- Thêm service xử lý upstream rename.
- Chuẩn hóa response: `ok`, `message`, `updated_summary`, `refresh_hint`.
- Log đủ context để debug nếu upstream đổi behavior.

### Phase 04 — Frontend View Toggle
- Thêm state `dashboardViewMode`.
- Đồng bộ view mode với storage để reload không mất lựa chọn.
- Đảm bảo switching không làm reload data thừa.
- Giữ nguyên các flow sync/delete/import hiện có.

### Phase 05 — Compact View Implementation
- Tạo compact workspace presentation giống hướng user chọn.
- Tối ưu mật độ thông tin, quick actions, slot display `members/7`.
- Gắn edit icon rename vào mỗi workspace.
- Giữ affordance rõ ràng để user vẫn hiểu action nào là sync, delete, manage.

### Phase 06 — Integration & State Safety
- Nối compact view vào action handlers hiện có.
- Nối rename mutation với targeted summary update.
- Đảm bảo SSE/sync events không ghi đè sai tên mới sau rename.
- Xử lý race: rename trong lúc sync hoặc delete.

### Phase 07 — Testing & QA Hardening
- Backend tests cho rename success/failure/not-found/upstream rejection.
- Frontend tests cho toggle mode, persistence, modal validation, optimistic-safe update.
- Manual QA checklist cho density, responsiveness, keyboard/mouse flow.
- Verify dashboard vẫn mượt với nhiều teams.

## Key Risks
- Upstream rename endpoint có thể là internal web flow, dễ thay đổi hơn API công khai.
- Nếu rename local trước khi backend xác nhận, UI dễ hiện tên sai.
- Compact view có thể làm action density cao hơn, tăng nguy cơ click nhầm nếu spacing không chuẩn.
- SSE/sync refresh có thể overwrite tên mới nếu source-of-truth update chưa được thiết kế đúng.

## Risk Controls
- Chỉ update tên trên UI sau khi backend trả `updated_summary` thật.
- Nếu rename thất bại, giữ nguyên tên cũ và hiển thị lỗi rõ.
- Không tái fetch full dashboard ngay khi toggle view.
- Với rename thành công, dùng targeted update + optional refresh nhẹ thay vì full reload mặc định.
- Thêm regression test cho race rename/sync/delete.

## Decision Rules
- Current View phải tiếp tục hoạt động y như hiện tại.
- Compact View dùng chung data source với Current View, chỉ khác presentation và interaction density.
- Rename chỉ được coi là thành công khi upstream/backend xác nhận.
- Không chấp nhận flow “đổi tên local cho đẹp” nếu tên thật chưa đổi.
- Nếu upstream rename cần quyền owner/admin, error copy phải nói rõ cho user.

## Recommended Order
1. `/design` để chốt API contract, modal flow, compact card structure.
2. `/visualize` nếu muốn mockup nhanh trước khi code.
3. `/code phase-01` để bắt đầu xác minh endpoint + guardrails.
4. Làm backend rename trước, rồi mới nối UI rename.
5. Hoàn tất test trước khi polish animation/micro-interaction.

## Quick Commands
- Thiết kế chi tiết: `/design`
- Xem UI trước: `/visualize`
- Bắt đầu code Phase 01: `/code phase-01`
- Xem bước tiếp: `/next`
- Lưu ngữ cảnh: `/save-brain`

## Notes
Plan này tập trung vào **mở rộng dashboard hiện có một cách an toàn**, không phải thay dashboard hiện tại bằng một implementation mới từ đầu.
