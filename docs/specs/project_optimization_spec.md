# Project Optimization Spec

## 1. Executive Summary
Mục tiêu của plan này là nâng cấp ChatGPT Team Manager từ một công cụ đã sử dụng được thành một hệ thống quản lý team có độ tin cậy cao trong thực tế vận hành. Trọng tâm không phải là thêm nhiều tính năng mới, mà là làm cho các tính năng hiện có:
- đúng hơn
- mượt hơn
- nhất quán hơn
- dễ bảo trì hơn

## 2. User Stories
- Là owner/admin, tôi muốn gửi invite rồi revoke ngay được nếu cần.
- Là người quản lý team, tôi muốn dashboard cập nhật nhanh mà không phải F5.
- Là người vận hành, tôi muốn biết workspace đang sync, lỗi hay đã ổn định.
- Là người bảo trì hệ thống, tôi muốn action response và sync rule rõ ràng để dễ debug.

## 3. Project Scope
### In scope
- Backend action contract
- Sync rules và source-of-truth
- Frontend state orchestration
- Dashboard responsiveness
- Regression tests
- Operational docs

### Out of scope
- Thêm module tính năng hoàn toàn mới
- Đổi công nghệ nền tảng
- Thiết kế lại UI theo hướng brand new product

## 4. Core Architecture Intent
### Backend
- Router mỏng hơn, tập trung nhận request/trả response
- Service/use-case layer gánh nghiệp vụ và fallback upstream
- Sync engine quyết định việc làm mới dữ liệu theo rule rõ ràng
- DB local là lớp cache vận hành có kiểm soát

### Frontend
- UI component tập trung hiển thị
- Hooks quản lý list/detail/event/actions
- Mutation update local có kiểm soát
- Refresh/invalidate theo phạm vi nhỏ nhất cần thiết

## 5. Source-of-Truth Matrix
| Data | Source of truth | Update timing | Frontend behavior |
|------|-----------------|---------------|-------------------|
| Workspace summary | DB local + sync metadata | Sau mutation hoặc sync | Update targeted, tránh full reload |
| Members list | DB local sau sync/detail refresh | Sau sync/detail refresh | Có thể optimistic remove ngắn hạn |
| Pending invites | DB local | Sau mutation + follow-up sync | Update local nếu có record thật |
| Current user role | DB local + token identity mapping | Sau sync/membership update | Không tự suy diễn ở UI |
| Sync status | Sync engine metadata | Real-time + polling/follow-up | Hiển thị rõ trạng thái hiện hành |

## 6. Flow Design Principles
1. Mutation phải trả về dữ liệu đủ để UI quyết định bước tiếp theo.
2. Không dùng placeholder nghiệp vụ cho ID thật.
3. Nếu upstream chưa xác nhận hoàn toàn, UI phải phản ánh là “đang đồng bộ”.
4. SSE chỉ là kênh tăng tốc cập nhật, không phải nơi giữ logic nghiệp vụ chính.
5. Nếu local update và background refresh cùng tồn tại, phải có rule ưu tiên rõ ràng.

## 7. Backend Planning Guidelines
- Chuẩn hóa response chung cho action:
  - `ok`
  - `message`
  - `affected_entity`
  - `updated_record`
  - `updated_summary`
  - `refresh_hint`
- Gom use-case theo nhóm:
  - invite
  - member
  - workspace
  - sync
- Bổ sung structured logging với context:
  - org_id
  - action
  - remote target id
  - fallback path used
  - result

## 8. Frontend Planning Guidelines
- Tách `page.tsx` thành các vùng trách nhiệm:
  - workspace list state
  - workspace detail state
  - action mutations
  - event connection
  - UI-only rendering
- Thiết lập refresh policy:
  - Local update ngay nếu đã có record thật
  - Invalidate detail khi mutation ảnh hưởng list con
  - Invalidate list khi mutation ảnh hưởng summary tổng
  - Full refresh chỉ dùng khi thật sự cần

## 9. Realtime & Refresh Policy
### Action categories
- Local-safe: Có thể update ngay bằng response thật
- Local-safe + detail refresh: Update ngay rồi refresh detail nền
- List-affecting: Update summary list có kiểm soát
- Sync-driven: Chỉ đổi trạng thái local, chờ sync/event xác nhận dữ liệu đầy đủ

### Event handling
- Event không nên ép full reload mặc định
- Event nên map vào:
  - update status cục bộ
  - invalidate list
  - invalidate detail
  - no-op nếu local state đã mới hơn

## 10. Testing Strategy
### Regression flows bắt buộc
- Invite -> revoke ngay
- Invite -> resend -> revoke
- Import workspace -> sync -> open details
- Kick member -> member list giảm -> summary cập nhật
- Manual sync khi sync đang chạy
- Delete workspace -> dashboard summary cập nhật đúng

### Coverage types
- Backend flow tests
- Backend contract tests
- Frontend state/render tests
- Manual QA checklist

## 11. Hidden Requirements
- Chống double click ở action nhạy cảm
- Trạng thái loading phải đủ rõ để user không thao tác lặp vô nghĩa
- Refactor từng lớp, tránh sửa sâu backend và frontend cùng lúc mà không có regression guard
- Khi fallback xảy ra, cần log để lần sau debug được

## 12. Tech Stack
- Next.js / React / TypeScript
- FastAPI / SQLAlchemy
- SQLite local cache
- SSE / EventSource
- Pytest + frontend tests

## 13. Build Checklist
- [ ] Baseline flows được ghi lại
- [ ] Backend action contract thống nhất
- [ ] Source-of-truth matrix được chốt
- [ ] Frontend hooks được tách khỏi `page.tsx`
- [ ] Refresh policy được ghi lại thành rule rõ ràng
- [ ] Regression tests pass
- [ ] Manual QA checklist pass
- [ ] Docs vận hành được cập nhật
