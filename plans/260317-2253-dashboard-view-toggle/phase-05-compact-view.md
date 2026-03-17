# Phase 05: Compact View Implementation
Status: ⬜ Pending
Dependencies: Phase 02, Phase 04

## Objective
Xây dựng giao diện `Compact View` giống hướng user mong muốn: gọn hơn, nhìn được nhiều team hơn, vẫn đẹp và thao tác nhanh.

## Requirements
### Functional
- [ ] Compact card/item hiển thị tên team, slot usage, pending, expiry, status.
- [ ] Có quick actions ngay trên item.
- [ ] Có icon edit cạnh tên team.
- [ ] Có entry point rõ để vào màn manage team/expanded details.

### Non-Functional
- [ ] Visual quality: vẫn premium, tối, hiện đại, không thành bảng khô cứng.
- [ ] Density: số item thấy được trên màn hình tăng rõ rệt so với current view.
- [ ] Interaction safety: icon spacing đủ để tránh click nhầm.

## Implementation Steps
1. [ ] Tạo component `CompactWorkspaceCard` hoặc tương đương.
2. [ ] Thiết kế layout item theo đúng thứ tự ưu tiên thông tin.
3. [ ] Hiển thị slot usage theo `member_count / member_limit` và optimize cho case `7 slots`.
4. [ ] Gắn status badge/syncing indicator gọn hơn current view.
5. [ ] Gắn action icons: rename, sync, delete, manage.
6. [ ] Tối ưu responsive behavior để compact view vẫn dùng tốt trên màn hình nhỏ hơn.
7. [ ] Đảm bảo style tokens thống nhất với dashboard hiện tại.

## Files to Create/Modify
- `frontend/src/components/compact-workspace-card.tsx` - component chính.
- `frontend/src/components/workspace-card.tsx` - giữ current view, chỉ chỉnh nếu cần API props đồng nhất.
- `frontend/src/app/page.tsx` - switch renderer.
- `frontend/src/app/globals.css` hoặc file CSS liên quan - style cho compact view.

## Test Criteria
- [ ] Compact view render đúng dữ liệu.
- [ ] Quick actions hoạt động đúng như current view.
- [ ] Dễ phân biệt workspace đang syncing, error, live.
- [ ] Không có layout shift lớn khi data cập nhật realtime.

## Notes
Compact view nên reuse logic nhiều nhất có thể từ current view để giảm bug và giảm chi phí bảo trì.

---
Next Phase: `phase-06-integration.md`
