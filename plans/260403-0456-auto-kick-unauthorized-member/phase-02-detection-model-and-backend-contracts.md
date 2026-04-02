# Phase 02: Detection Model & Backend Contracts

Status: ⬜ Pending
Dependencies: Phase 01

## Objective

Định nghĩa cấu trúc dữ liệu và contract backend cần có để unauthorized detection trở thành một phần chính thức của hệ thống.

## Requirements

### Functional

- [ ] Có model lưu policy mode theo workspace.
- [ ] Có model hoặc structure lưu unauthorized findings.
- [ ] API/dashboard đọc được trạng thái unauthorized hiện tại.
- [ ] Có reason code rõ ràng cho detection và enforcement.

### Non-Functional

- [ ] Contract response nhất quán, dễ dùng cho frontend.
- [ ] Dữ liệu đủ giàu để debug nhưng không quá rối.
- [ ] Không buộc frontend phải tự suy luận logic nghiệp vụ phức tạp.

## Implementation Steps

1. [ ] Chốt field cho workspace policy: `mode`, `enabled_at`, `updated_at`.
2. [ ] Chốt field cho unauthorized finding: `org_id`, `email`, `member_remote_id`, `detected_at`, `reason`, `status`.
3. [ ] Chốt status lifecycle: `detected`, `kick_scheduled`, `kicked`, `ignored`, `trusted`, `kick_failed`.
4. [ ] Chốt API response shape cho workspace detail để frontend render unauthorized members.
5. [ ] Chốt action response shape cho manual kick/trust/toggle policy.

## Files to Create/Modify

- `backend/app/models.py` - bổ sung policy/finding tables nếu chọn persist.
- `backend/app/schemas.py` - response/request schemas.
- `backend/app/routers/workspaces.py` - expose policy/detail data.
- `backend/app/routers/members.py` - action contracts nếu cần.

## Test Criteria

- [ ] Contract examples đủ rõ cho frontend dùng.
- [ ] Có phân biệt rõ trạng thái detection và trạng thái enforcement.
- [ ] Có decision rõ finding nào persist, finding nào chỉ computed tạm.

## Notes

Phase này nên chốt “dùng dữ liệu gì để hiển thị” trước khi code detection sâu, tránh backend làm xong nhưng frontend không có shape chuẩn để dùng.

---

Next Phase: `phase-03-sync-pipeline-detection-logic.md`
