# Dashboard View Toggle and Real Workspace Rename Spec

## 1. Executive Summary
Feature này mở rộng dashboard quản lý workspace theo 2 hướng cùng lúc:
1. **Cải thiện khả năng quản lý khi có nhiều team** bằng cách thêm `Compact View` song song với `Current View`.
2. **Cho phép đổi tên workspace thật** ngay trong dashboard bằng icon edit cạnh tên team.

Mục tiêu không chỉ là thêm UI mới, mà là làm sao để:
- nhìn được nhiều team hơn,
- thao tác nhanh hơn,
- vẫn giữ cảm giác dashboard premium,
- và không phá độ ổn định/realtime behavior hiện có.

## 2. Product Intent
Dashboard hiện tại phù hợp khi số team vừa phải. Khi số lượng team tăng, người dùng phải scroll lâu, khó quét nhanh và thao tác lặp lại nhiều. Feature này thêm một chế độ hiển thị dày thông tin hơn, nhưng vẫn reuse source dữ liệu và action logic hiện có để hạn chế bug.

Rename workspace là phần giá trị cao vì nó cho phép quản lý tên team thật ngay trong công cụ, không phải đổi tay ở nơi khác rồi quay lại sync.

## 3. User Stories
- Là người quản lý nhiều team, tôi muốn chuyển dashboard sang chế độ gọn hơn để thấy nhiều team hơn trên một màn hình.
- Là người vận hành, tôi muốn đổi tên team ngay trong dashboard để tên hiển thị khớp với team thật.
- Là user đang theo dõi sync, tôi muốn việc đổi view không làm dashboard lag hoặc reload lung tung.
- Là người quản trị, tôi muốn rename chỉ thành công khi hệ thống đổi được tên thật, không phải chỉ đổi local.
- Là người bảo trì, tôi muốn flow rename có test và log đủ rõ để debug nếu upstream đổi behavior.

## 4. Scope
### In scope
- Toggle 2 mode dashboard.
- Compact presentation mode giống hướng user mong muốn.
- Workspace rename bằng backend/upstream.
- Summary update targeted sau rename.
- Tests và QA checklist.

### Out of scope
- Đổi route hoặc kiến trúc tổng thể của dashboard.
- Bulk edit nhiều workspace.
- Refactor sâu toàn bộ `page.tsx` vượt quá nhu cầu feature.

## 5. UX Contract
### 5.1 Dashboard header
Header sẽ có thêm control chuyển mode, đặt gần khu vực action chính.

Ví dụ:
- `Current View`
- `Compact View`

Control phải có:
- active state rõ,
- click area đủ lớn,
- không chiếm quá nhiều chỗ,
- hoạt động độc lập với việc tải data.

### 5.2 Current View
- Giữ nguyên layout hiện tại.
- Có thể thêm icon edit nếu muốn đồng nhất với compact view.
- Không thay đổi flow expand/manage/sync/delete đang hoạt động ổn định.

### 5.3 Compact View
Mỗi workspace item cần hiển thị tối thiểu:
- Tên team
- Slot usage: `member_count / member_limit`
- Pending invites
- Token expiry / expiry countdown
- Status: `live`, `syncing`, `error`
- Quick actions: rename, sync, delete, manage/open

Compact view phải:
- nhìn được nhiều item hơn current view,
- không làm user khó đọc,
- vẫn có hierarchy rõ giữa tên team và số liệu phụ,
- giữ style premium/dark như dashboard hiện có.

### 5.4 Rename interaction
Flow rename đề xuất:
1. User bấm icon edit cạnh tên team.
2. Mở dialog hoặc inline popover có input tên mới.
3. Input được prefill bằng tên hiện tại.
4. User submit.
5. UI hiện loading/disabled state.
6. Nếu backend thành công:
   - đóng dialog,
   - cập nhật tên mới trên dashboard,
   - có toast success ngắn gọn.
7. Nếu backend thất bại:
   - giữ dialog hoặc đóng tùy pattern được chọn,
   - tên cũ vẫn giữ nguyên,
   - báo lỗi rõ.

## 6. Data Ownership / Source of Truth
| Field | Source of truth | UI update policy |
|------|------------------|------------------|
| `name` | Backend DB local sau upstream rename success | Chỉ update UI khi có `updated_summary` thật |
| `member_count` | Workspace summary từ backend | Không tự suy diễn từ rename flow |
| `member_limit` | Workspace summary từ backend | Read-only trong feature này |
| `pending_invites` | Workspace summary / detail refresh | Chỉ refresh khi mutation khác ảnh hưởng |
| `status` | Sync metadata từ backend/SSE | Compact view chỉ render lại theo nguồn hiện có |
| `expires_at` | Workspace summary từ backend | Không tự chỉnh local |
| `sync_reason` / `is_hot` | SSE + backend summary | Không được rename flow ghi đè sai |

## 7. Functional Design
### 7.1 View mode persistence
- View mode lưu ở localStorage.
- Lần đầu vào trang dùng default là `current`.
- Nếu localStorage có giá trị hợp lệ thì restore ngay sau hydrate.
- Chuyển mode không trigger full data refetch mặc định.

### 7.2 Shared action model
Cả `Current View` và `Compact View` phải dùng chung action handlers hiện có để tránh logic lệch nhau:
- sync
- delete
- manage/open details
- rename (mới)

### 7.3 Rename validation
Input rename cần chặn tối thiểu:
- chuỗi rỗng,
- toàn khoảng trắng,
- quá dài,
- trùng hệt tên cũ,
- ký tự không hợp lệ nếu upstream có rule rõ.

### 7.4 Rename success behavior
Khi rename thành công, backend trả về:
- `ok`
- `message`
- `updated_summary`
- `refresh_hint`

Frontend:
- apply `updated_summary` targeted vào list hiện tại,
- giữ nguyên mode đang xem,
- không reset expanded/detail state nếu không cần.

### 7.5 Rename failure behavior
Nếu rename thất bại:
- tên cũ vẫn giữ nguyên,
- không mutate local summary,
- hiện toast/error text rõ,
- dialog có thể giữ mở để user sửa lại.

## 8. Backend API Contract
### Proposed endpoint
`PATCH /api/workspaces/{org_id}/name`

### Request body
```json
{
  "name": "New Workspace Name"
}
```

### Success response
```json
{
  "ok": true,
  "message": "Workspace renamed successfully",
  "updated_summary": {
    "org_id": "org_001",
    "name": "New Workspace Name"
  },
  "refresh_hint": {
    "scope": "workspace_list",
    "reason": "workspace_renamed",
    "org_id": "org_001",
    "include_details": false
  }
}
```

### Failure cases
- `400`: invalid name
- `401/403`: token or permission issue
- `404`: workspace not found
- `409`: rename conflict or invalid current state
- `502`: upstream rename failed

## 9. Integration Notes
### Backend responsibilities
- Validate input.
- Load workspace from DB local.
- Resolve token/access path.
- Call upstream rename.
- Persist new name locally only after upstream success.
- Return consistent action contract.

### Frontend responsibilities
- Open/close rename UI.
- Prevent duplicate submit.
- Apply targeted summary update only on confirmed success.
- Respect `refresh_hint` nếu backend yêu cầu refresh thêm.

## 10. Race Conditions to Design For
1. **Rename while sync is running**
   - Tên mới không được bị sync cũ ghi đè lại nếu upstream đã đổi thành công.
2. **Rename while delete confirmation is open**
   - Nếu workspace bị delete trước, rename phải fail an toàn.
3. **Rename request succeeds but list refresh lags**
   - `updated_summary` phải đủ để UI cập nhật ngay.
4. **SSE event arrives after rename**
   - Event handling không được vô tình restore tên cũ từ summary stale.
5. **User switches view during rename**
   - Modal/state không được làm crash app; tối thiểu phải gracefully close hoặc continue đúng.

## 11. Performance Rules
- View mode switch = presentation swap, không phải data reload flow.
- Reuse `sortedWorkspaces` và existing state càng nhiều càng tốt.
- Memo hóa compact item component nếu list dài.
- Không attach thêm EventSource mới chỉ vì đổi view.
- Rename success ưu tiên targeted update thay vì full list reload.

## 12. Testing Strategy
### Backend
- Rename success
- Invalid name
- Missing workspace
- Upstream reject
- Permission/token failure
- Delete-before-persist race nếu feasible

### Frontend
- Toggle between views
- Persist view mode after reload
- Compact view renders correct summary fields
- Open rename dialog from compact item
- Rename success updates visible title
- Rename failure leaves old title unchanged
- Switch view while rename dialog open

### Manual QA
- Dashboard với nhiều teams
- Current view vẫn hoạt động như cũ
- Compact view bớt scroll rõ rệt
- Sync/Delete/Import không bị gãy sau khi thêm toggle
- Rename thật phản ánh chính xác ở dashboard sau refresh/reopen

## 13. Hidden Requirements
- Button/icon cần `id` rõ ràng để test browser được.
- Toast copy phải dễ hiểu với user vận hành.
- Không để rename flow làm `page.tsx` phình to thêm nhiều logic inline; nên tách component/hook hợp lý.
- Nếu rename upstream phụ thuộc internal endpoint, phải bọc service để sau này dễ hotfix.

## 14. Recommended Implementation Order
1. Xác nhận upstream rename path.
2. Tạo backend rename endpoint + tests.
3. Tạo toggle state + persistence.
4. Tạo compact view component.
5. Nối rename dialog vào compact/current view.
6. Hardening bằng tests + manual QA.

## 15. Build Checklist
- [ ] Chốt rename upstream mechanism
- [ ] Có backend endpoint rename
- [ ] Có compact view component
- [ ] Có toggle persisted qua reload
- [ ] Current view không regress
- [ ] Rename success update đúng summary
- [ ] Rename failure rollback-safe
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Manual QA pass
