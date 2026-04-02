# Phase 05: Dashboard Visibility & Controls

Status: ⬜ Pending
Dependencies: Phase 04

## Objective

Hiển thị unauthorized members rõ ràng trên dashboard và cho phép user vận hành policy theo từng workspace.

## Requirements

### Functional

- [ ] Workspace detail hiển thị danh sách unauthorized members.
- [ ] Có badge/indicator để biết workspace đang có finding.
- [ ] Có UI bật/tắt mode policy theo workspace.
- [ ] Có action thủ công phù hợp (`Kick now`, `Trust member`, hoặc ít nhất `Kick now`).

### Non-Functional

- [ ] Copy/label dễ hiểu, không mơ hồ.
- [ ] Không làm dashboard rối hoặc quá nặng.
- [ ] Update UI phải bám đúng backend source-of-truth.

## Implementation Steps

1. [ ] Chốt vị trí hiển thị unauthorized section trong workspace detail.
2. [ ] Chốt badge/summary trên workspace card nếu có finding.
3. [ ] Thiết kế control đổi mode `off / warn_only / auto_kick`.
4. [ ] Thiết kế action button và confirm flow cho manual kick.
5. [ ] Thiết kế trạng thái loading / kicked / failed / trusted.
6. [ ] Nối UI với backend contracts đã chốt ở Phase 02.

## Files to Create/Modify

- `frontend/src/app/page.tsx` - nối unauthorized state vào dashboard flow hiện tại.
- `frontend/src/components/*` - unauthorized panel, badges, actions.
- `frontend/src/lib/types.ts` - types cho policy/finding nếu có.
- `frontend/tests/*` - UI tests/interaction tests.

## Test Criteria

- [ ] Workspace có finding hiển thị đúng count.
- [ ] Toggle policy mode phản ánh đúng state backend.
- [ ] Manual kick action update UI đúng.
- [ ] Failure state hiển thị rõ, không biến mất mơ hồ.

## Notes

UI của phase này nên ưu tiên “rõ và đáng tin” hơn là cầu kỳ. User phải nhìn phát biết workspace nào đang có member lạ.

---

Next Phase: `phase-06-integration-safety-and-state-consistency.md`
