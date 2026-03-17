# Phase 02: UX Contract & Data Mapping
Status: ⬜ Pending
Dependencies: Phase 01

## Objective
Chốt chính xác người dùng sẽ thấy gì, bấm gì, và dữ liệu nào được tin là thật trong từng view để lúc code không phải sửa logic qua lại.

## Requirements
### Functional
- [ ] Có toggle rõ ràng giữa `Current View` và `Compact View`.
- [ ] Compact view hiển thị đủ thông tin quan trọng mà không bị rối.
- [ ] Rename flow có modal hoặc inline form rõ ràng.
- [ ] Hiển thị slot theo dạng `member_count / 7` khi giới hạn là 7.

### Non-Functional
- [ ] Clarity: action icon không gây hiểu nhầm.
- [ ] Speed: chuyển view gần như tức thì vì chỉ đổi layout.
- [ ] Accessibility: keyboard focus và button labels rõ ràng.

## Implementation Steps
1. [ ] Chốt vị trí toggle trong dashboard header.
2. [ ] Định nghĩa compact card anatomy: title, owner badge/status, slot usage, pending, expiry, action row.
3. [ ] Chốt phần nào click để mở detail/manage team.
4. [ ] Chốt edit icon behavior: open modal, prefill current name, validate, submit.
5. [ ] Chốt error/success copy cho rename.
6. [ ] Viết source-of-truth matrix cho các field sau rename/sync:
   - workspace name
   - member_count
   - pending_invites
   - status
   - expires_at
7. [ ] Chốt persistence behavior cho view mode (localStorage/session-safe).

## Files to Create/Modify
- `docs/specs/dashboard_view_toggle_and_rename_spec.md` - nguồn spec chính.
- `frontend/src/app/page.tsx` - chèn toggle orchestration.
- `frontend/src/components/workspace-card.tsx` - đối chiếu current view.
- `frontend/src/components/compact-workspace-card.tsx` - component mới dự kiến.

## Test Criteria
- [ ] Có mô tả UI states đầy đủ cho toggle và rename.
- [ ] Có source-of-truth rule rõ để tránh UI sai sau sync.
- [ ] Có acceptance criteria cho compact view density.

## Notes
Đây là phase chốt “luật chơi”. Càng rõ ở đây thì Phase 04-06 càng ít bug.

---
Next Phase: `phase-03-backend-rename.md`
