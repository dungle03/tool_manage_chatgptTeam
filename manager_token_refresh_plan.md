# Kế hoạch tích hợp token refresher vào `tool_manage_chatgptTeam`

## 1. Mục tiêu

Mục tiêu của việc tích hợp là biến manager thành nơi điều khiển chính cho việc làm mới token, người dùng gần như không còn phải cập nhật token bằng tay nữa.

Sau khi hoàn thành, hệ thống cần đạt được các hành vi sau:

1. Trên mỗi card workspace/team, người dùng bấm vào **nút token hiện tại**
2. Manager tự xác định đúng account owner của team đó
3. Manager gọi `chatgpt_token_refresher` để lấy token mới cho đúng team
4. Sau khi refresh token thành công, manager **tự sync luôn workspace đó**
5. Nếu token sắp hết hạn, hệ thống **tự refresh nền và tự sync** mà không cần người dùng thao tác
6. Nếu việc refresh lỗi, hệ thống báo lỗi ngắn gọn, dễ hiểu, và vẫn giữ đường lui là cập nhật token thủ công khi cần

---

## 2. Phạm vi của tích hợp

### 2.1 Vai trò của từng hệ thống

#### `tool_manage_chatgptTeam`

- là giao diện điều khiển chính
- là nơi người dùng thao tác hằng ngày
- chịu trách nhiệm điều phối refresh, update token, sync team, hiển thị trạng thái

#### `chatgpt_token_refresher`

- là công cụ phụ trợ phía sau
- chỉ chịu trách nhiệm đăng nhập / lấy token mới cho đúng account
- không phải nơi người dùng thao tác trực tiếp trong flow thường ngày

### 2.2 Kết quả mong muốn về trải nghiệm

Người dùng không cần:

- copy/paste token thủ công thường xuyên
- mở tool refresher riêng
- nhớ token nào sắp hết hạn

Thay vào đó, flow chuẩn sẽ là:

- **Bấm 1 nút trên manager → token được refresh → team được sync**

---

## 3. Quy tắc nghiệp vụ đã chốt

## 3.1 Cách xác định account dùng để refresh

Manager sẽ **không dùng email cấu hình tay cho từng workspace**.

Thay vào đó, manager sẽ tự suy ra email refresh từ danh sách member của chính workspace đó theo rule cố định:

1. Chỉ xét các member có role là **owner**
2. Nếu có đúng 1 owner:
   - dùng email của owner đó
3. Nếu có nhiều owner:
   - chọn **owner có thời gian tham gia team sớm nhất**
4. Nếu không có owner:
   - không thể refresh tự động cho workspace đó
   - trả lỗi ngắn gọn để người dùng biết lý do

## 3.2 Quy tắc chọn “owner tham gia sớm nhất”

Để triển khai ổn định, cần thống nhất thứ tự ưu tiên khi xác định owner sớm nhất:

1. ưu tiên `created_at` sớm nhất
2. nếu thiếu `created_at`, fallback sang `invite_date` sớm nhất
3. nếu cả hai đều thiếu hoặc dữ liệu không đủ rõ:
   - dùng một fallback ổn định, ví dụ `id` nhỏ nhất trong DB

Mục tiêu là để cùng một workspace luôn cho ra cùng một owner email khi refresh.

## 3.3 Giả định về dữ liệu refresher

- file `accounts.txt` là đúng và đầy đủ
- không cần xây thêm logic xử lý trường hợp file tài khoản bị sai
- hệ thống được phép giả định rằng nếu email owner tồn tại trong team thì email đó cũng tồn tại đúng trong refresher data source

## 3.4 Hành vi sau khi refresh token

Khi người dùng bấm refresh token cho một workspace:

1. lấy token mới
2. update token vào manager
3. sync luôn workspace đó

Nói cách khác, flow refresh mới phải tương đương với việc:

- nhập token tay như hiện tại
- rồi sync workspace

nhưng được tự động hóa hoàn toàn.

## 3.5 Trạng thái “thành công một phần”

Có một tình huống cần hỗ trợ rõ ràng:

- refresh token thành công
- token đã được lưu vào DB
- nhưng bước sync sau đó bị lỗi

Trường hợp này **không nên coi là fail hoàn toàn**.
Nó phải được biểu diễn là:

- **thành công một phần**

UI và API response cần thể hiện rõ:

- token đã được cập nhật
- nhưng dữ liệu workspace chưa sync xong

## 3.6 Quy tắc auto-refresh nền

Auto-refresh sẽ áp dụng cho **tất cả workspace** đủ điều kiện, không yêu cầu bật riêng từng team.

Một workspace đủ điều kiện auto-refresh nếu:

- có `access_token_expires_at`
- token còn dưới 1 ngày là hết hạn
- workspace chưa bị chặn auto-refresh do lỗi lặp lại

Nếu nhiều workspace cùng tới hạn:

- xử lý tối đa **3 team cùng lúc**
- xong 1 batch thì **nghỉ 1 phút**
- sau đó mới xử lý batch tiếp theo

Mục tiêu là tránh việc mở quá nhiều browser session cùng lúc, gây block hoặc làm hệ thống mất ổn định.

## 3.7 Khi auto-refresh lỗi nhiều lần

Nếu một workspace auto-refresh thất bại liên tiếp nhiều lần:

- dừng auto-refresh cho workspace đó
- đánh dấu trạng thái cần xử lý thủ công
- báo rõ cho người dùng biết team đó cần cập nhật tay

## 3.8 Manual fallback

Dù mục tiêu là không phải cập nhật token bằng tay nữa, hệ thống vẫn cần giữ manual update như một đường lui an toàn.

Tuy nhiên:

- manual update không còn là luồng chính
- nên được ẩn ở UI phụ, advanced section, hoặc menu fallback

---

## 4. Kiến trúc tích hợp tổng thể

```text
Frontend workspace card
-> POST /api/workspaces/{id}/refresh-token
-> Backend resolve owner email từ workspace members
-> Backend gọi subprocess tới main_camoufox.py --email <owner_email>
-> Refresher tạo output JSON chuẩn
-> Backend đọc JSON, verify token đúng workspace
-> Backend update access token + expiry
-> Backend sync workspace ngay sau đó
-> Frontend nhận trạng thái success / partial success / failed
```

Auto-refresh nền cũng sẽ dùng lại đúng flow này, chỉ khác ở chỗ trigger đến từ scheduler thay vì người dùng bấm nút.

---

## 5. Thiết kế dữ liệu cần có ở manager

## 5.1 Dữ liệu đã có thể tận dụng

Từ code hiện tại, manager đã có nhiều phần phù hợp:

- `Workspace.org_id`
- `Workspace.account_id`
- `Workspace.access_token`
- `Member.email`
- `Member.role`
- `Member.created_at`
- `Member.invite_date`

Đây là nền tảng đủ để suy ra owner email và verify token sau refresh.

## 5.2 Dữ liệu nên chuẩn hóa thêm

Để phục vụ auto-refresh và tracking trạng thái, manager nên có hoặc chuẩn hóa các field sau ở `Workspace`:

- `access_token_expires_at`
- `last_token_refresh_at`
- `last_token_refresh_error`
- `token_refresh_fail_count`
- `token_refresh_blocked`

### Gợi ý ý nghĩa từng field

- `access_token_expires_at`: thời điểm token hiện tại hết hạn
- `last_token_refresh_at`: lần refresh gần nhất
- `last_token_refresh_error`: lỗi refresh gần nhất nếu có
- `token_refresh_fail_count`: số lần refresh lỗi liên tiếp
- `token_refresh_blocked`: cờ chặn auto-refresh cho workspace đó

Các field này giúp:

- xác định team nào sắp hết hạn
- biết team nào đang lỗi liên tục
- hiển thị cảnh báo đơn giản ở UI

---

## 6. Backend service cần xây dựng

## 6.1 Helper chọn owner email

Cần tạo một helper rõ ràng, ví dụ:

- `resolve_workspace_owner_email(workspace, session)`

### Nhiệm vụ của helper

1. query member của workspace
2. lọc member có role `owner`
3. áp dụng rule chọn owner sớm nhất
4. trả về email owner được chọn
5. nếu không có owner thì raise domain error rõ ràng

### Yêu cầu bắt buộc

- cùng một dữ liệu đầu vào phải cho cùng một kết quả
- không chọn admin
- không chọn đại email đầu tiên ngẫu nhiên

---

## 6.2 Service gọi token refresher

Cần tạo service mới, ví dụ:

- `backend/app/services/token_refresher.py`

### Nhiệm vụ của service này

1. nhận `workspace`
2. resolve owner email
3. tạo output file tạm
4. gọi subprocess tới `main_camoufox.py`
5. đọc JSON output
6. parse kết quả
7. verify token đúng workspace
8. trả payload chuẩn hóa cho router/service cao hơn
9. xóa file tạm sau khi dùng xong

### Input đề xuất

- `workspace`
- `session`
- `mode`: manual hoặc auto (để log/telemetry nếu cần)

### Output đề xuất

Một object nội bộ, ví dụ:

```python
{
    "owner_email": "owner@gmail.com",
    "access_token": "eyJ...",
    "account_id": "acc_xxx",
    "organization_id": "org_xxx",
    "success": True,
    "error": None,
}
```

Nếu fail, service phải trả lỗi đủ rõ để tầng trên chuyển thành thông báo ngắn gọn cho người dùng.

---

## 6.3 Service verify token result

Sau khi refresher trả JSON, manager phải kiểm tra token đó có thực sự thuộc workspace đang xử lý không.

### Rule verify

#### Ưu tiên 1: `account_id`

Nếu workspace có `account_id` và result có `account_id`:

- hai giá trị này phải khớp

#### Fallback: `organization_id`

Nếu cần fallback:

- `organization_id` từ result phải khớp với `workspace.org_id`

### Nếu mismatch

- dừng flow
- không update DB
- trả lỗi ngắn gọn

Ví dụ:

- `Token does not match this workspace`

---

## 6.4 Service lưu token mới

Sau khi verify thành công, manager cần cập nhật:

- `workspace.access_token`
- `workspace.access_token_expires_at`
- `workspace.last_token_refresh_at`
- reset `workspace.last_token_refresh_error`
- reset `workspace.token_refresh_fail_count`
- `workspace.token_refresh_blocked = false`

### Lấy `access_token_expires_at`

Nên decode access token để lấy claim `exp`, rồi convert thành UTC datetime.

### Lưu ý

Việc update token nên được commit xong trước khi bước sync bắt đầu, để nếu sync fail thì token mới vẫn được giữ lại.

---

## 7. Cấu hình backend cần có

Không nên hardcode đường dẫn refresher trong code.

### Các config nên thêm

- `TOKEN_REFRESHER_PYTHON`
- `TOKEN_REFRESHER_SCRIPT`
- `TOKEN_REFRESHER_WORKDIR`
- `TOKEN_REFRESHER_TIMEOUT_SECONDS`

### Ý nghĩa

- `TOKEN_REFRESHER_PYTHON`: python executable dùng để chạy refresher
- `TOKEN_REFRESHER_SCRIPT`: đường dẫn tới `main_camoufox.py`
- `TOKEN_REFRESHER_WORKDIR`: working directory của refresher
- `TOKEN_REFRESHER_TIMEOUT_SECONDS`: timeout cho subprocess

### Khuyến nghị timeout

- manual refresh: 180–300 giây
- auto-refresh: 300 giây

---

## 8. API cần xây dựng

## 8.1 API manual refresh cho một workspace

### Endpoint đề xuất

```http
POST /api/workspaces/{id}/refresh-token
```

### Mục tiêu

Dùng cho nút token hiện tại trên card workspace.

### Flow chi tiết

1. tìm workspace theo `org_id`
2. nếu không tồn tại -> trả 404
3. resolve owner email từ member list
4. gọi token refresher service
5. verify token đúng workspace
6. lưu token mới + expiry vào DB
7. gọi sync cho workspace đó
8. trả response theo trạng thái phù hợp

### Các trạng thái response cần hỗ trợ

#### Success

- refresh token thành công
- sync thành công

#### Partial success

- refresh token thành công
- sync thất bại
- token mới vẫn đã được lưu

#### Failed

- refresh thất bại từ trước bước lưu token
- hoặc verify mismatch
- hoặc không tìm thấy owner

### Dữ liệu response gợi ý

```json
{
  "ok": true,
  "status": "success | partial_success | failed",
  "message": "...",
  "workspace_id": "org_xxx",
  "owner_email": "owner@gmail.com",
  "token_updated": true,
  "sync_completed": false
}
```

---

## 8.2 API manual token update vẫn giữ lại

API update token thủ công hiện có vẫn nên được giữ, nhưng không còn là flow chính.

### Vai trò của API này

- fallback khi refresher bị lỗi
- fallback khi auto-refresh bị block
- công cụ cứu hộ khi cần xử lý tay

---

## 9. Flow giao diện người dùng

## 9.1 Nút token hiện tại trên card workspace

Nút token hiện có sẽ trở thành nút:

- **Refresh Token**

### Khi người dùng bấm nút

Frontend gọi:

```http
POST /api/workspaces/{id}/refresh-token
```

### UI state cần có

- loading khi request đang chạy
- disable nút trong lúc đang xử lý
- hiển thị toast hoặc message ngắn gọn khi hoàn tất

---

## 9.2 Nội dung thông báo cho người dùng

Thông báo nên ngắn, rõ, không quá kỹ thuật.

### Nếu success hoàn toàn

- `Refreshed token and synced workspace successfully`

### Nếu thành công một phần

- `Token refreshed successfully, but sync failed`

### Nếu lỗi không có owner

- `No owner found for this workspace`

### Nếu owner không có trong refresher

- `Owner account not found in refresher`

### Nếu refresher timeout

- `Token refresh timed out`

### Nếu browser automation lỗi

- `Browser refresh failed`

### Nếu token không khớp workspace

- `Token does not match this workspace`

### Nếu auto-refresh bị chặn do lỗi lặp lại

- `Auto-refresh paused. Manual update required`

---

## 9.3 Manual fallback trên UI

Manual update vẫn cần tồn tại nhưng không nằm ở vị trí nổi bật như flow chính.

### Gợi ý triển khai

- đưa vào menu “More” hoặc “Advanced”
- hoặc chỉ hiện khi refresh auto thất bại

Mục tiêu là:

- giao diện chính vẫn sạch
- nhưng vẫn có đường cứu hộ khi cần

---

## 10. Auto-refresh nền

## 10.1 Mục tiêu

Nếu token sắp hết hạn thì manager tự xử lý trước, để hạn chế tối đa việc người dùng phải bấm tay.

## 10.2 Điều kiện chọn workspace cần auto-refresh

Một workspace được xếp vào danh sách auto-refresh nếu:

- có `access_token_expires_at`
- `access_token_expires_at <= now + 1 day`
- `token_refresh_blocked != true`

## 10.3 Lịch chạy scheduler

Có thể chạy kiểm tra định kỳ mỗi:

- 30 phút
- hoặc 1 giờ

Không cần chạy quá dày, vì token có tuổi thọ khoảng 9 ngày.

## 10.4 Quy tắc xử lý theo batch

Nếu có nhiều workspace cùng tới hạn:

1. nhóm thành từng batch
2. mỗi batch xử lý tối đa **3 workspace cùng lúc**
3. kết thúc batch thì **nghỉ 1 phút**
4. tiếp tục batch kế tiếp

### Mục đích

- tránh mở quá nhiều browser instance cùng lúc
- giảm nguy cơ block
- giảm tải tài nguyên máy

---

## 10.5 Flow auto-refresh của từng workspace

Flow mỗi workspace trong auto mode cũng giống manual mode:

1. resolve owner email
2. gọi refresher subprocess
3. verify token
4. lưu token mới
5. sync workspace
6. cập nhật trạng thái success / partial success / failed

---

## 10.6 Khi auto-refresh lỗi nhiều lần

Cần có ngưỡng chặn, ví dụ:

- fail liên tiếp 3 lần

Sau ngưỡng đó:

- set `token_refresh_blocked = true`
- ghi `last_token_refresh_error`
- hiển thị cảnh báo đỏ ở UI
- yêu cầu manual update

### Lưu ý

Manual refresh vẫn có thể được phép chạy ngay cả khi auto-refresh đã bị block.

---

## 11. Concurrency, locking, và an toàn vận hành

Để tránh race condition, cần có cơ chế đảm bảo rằng cùng một workspace không bị refresh chồng chéo.

## 11.1 Lock theo workspace

Một workspace tại một thời điểm chỉ nên có **1 refresh flow** đang chạy.

### Áp dụng cho cả:

- user bấm refresh tay
- auto-refresh nền
- các trigger khác nếu có sau này

Nếu workspace đang refresh mà lại có request mới:

- bỏ qua request sau
- hoặc trả về trạng thái “đang xử lý”

## 11.2 Tách transaction hợp lý

Nên tách logic thành 2 bước rõ:

### Bước 1

refresh token và commit token mới

### Bước 2

sync workspace

Lợi ích:

- nếu sync fail, token mới vẫn còn
- hỗ trợ trạng thái partial success đúng bản chất

## 11.3 Timeout và cleanup

- subprocess phải có timeout
- file output tạm phải được xóa
- lỗi timeout phải được normalize thành message ngắn gọn

---

## 12. Logging và quan sát vận hành

Người dùng không cần log chi tiết dài dòng, nhưng backend vẫn nên có log đủ để debug khi cần.

## 12.1 Những gì nên log

- workspace nào đang refresh
- owner email nào được chọn
- có nhiều owner hay không
- refresher chạy thành công hay fail
- verify token có khớp hay không
- sync có thành công hay không
- workspace có bị block auto-refresh hay không

## 12.2 Những gì cần hiển thị cho UI

UI chỉ cần mức ngắn gọn:

- thành công
- thành công một phần
- thất bại
- lỗi gần nhất nếu cần

---

## 13. Các lỗi chuẩn hóa nên có

Manager nên dùng tập lỗi ngắn, nhất quán, để frontend hiển thị dễ hiểu.

### Nhóm lỗi xác định owner

- `No owner found for this workspace`
- `Multiple owners found, using earliest joined owner`

### Nhóm lỗi refresher

- `Owner account not found in refresher`
- `Token refresh timed out`
- `Browser refresh failed`
- `Invalid refresher output`

### Nhóm lỗi verify

- `Token does not match this workspace`

### Nhóm lỗi sync

- `Token refreshed, but sync failed`

### Nhóm lỗi auto mode

- `Auto-refresh paused. Manual update required`

---

## 14. Test plan

## 14.1 Backend tests

### A. Owner resolution

- 1 owner -> chọn đúng owner đó
- nhiều owner -> chọn owner tham gia sớm nhất
- không có owner -> lỗi đúng

### B. Refresher subprocess

- chạy subprocess thành công
- output JSON hợp lệ
- subprocess timeout
- output JSON lỗi format

### C. Token verify

- `account_id` khớp -> pass
- fallback `organization_id` khớp -> pass
- cả hai mismatch -> fail

### D. Manual refresh endpoint

- refresh OK + sync OK -> success
- refresh OK + sync fail -> partial success
- refresh fail -> failed

### E. Auto-refresh scheduler

- chỉ pick workspace còn dưới 1 ngày
- không pick workspace bị block
- tối đa 3 workspace cùng lúc
- nghỉ 1 phút giữa batch

### F. Failure blocking

- fail liên tiếp đủ ngưỡng -> block auto-refresh
- manual refresh vẫn có thể dùng như fallback

## 14.2 Frontend tests

- nút token gọi đúng endpoint mới
- loading state hoạt động đúng
- success toast đúng
- partial success toast đúng
- failed toast đúng
- manual fallback vẫn mở được khi cần

---

## 15. Thứ tự triển khai khuyến nghị

### Bước 1

Chuẩn hóa lưu `access_token_expires_at`

### Bước 2

Viết helper resolve owner email từ member list

### Bước 3

Tạo `token_refresher.py` service gọi Camoufox

### Bước 4

Thêm verify token result với workspace

### Bước 5

Tạo endpoint `POST /api/workspaces/{id}/refresh-token`

### Bước 6

Nối nút token hiện tại ở frontend vào endpoint này

### Bước 7

Ẩn manual token update vào fallback UI

### Bước 8

Tạo scheduler auto-refresh nền theo batch 3 team + nghỉ 1 phút

### Bước 9

Thêm logic block auto-refresh khi lỗi lặp lại

### Bước 10

Hoàn thiện test và hardening

---

## 16. Deliverables mong muốn

### Backend

- [ ] có helper resolve owner email cho workspace
- [ ] có service gọi refresher subprocess
- [ ] có verify token đúng workspace
- [ ] có API refresh token + sync cho 1 workspace
- [ ] có lưu `access_token_expires_at`
- [ ] có state tracking cho auto-refresh failures
- [ ] có scheduler auto-refresh theo batch giới hạn

### Frontend

- [ ] nút token hiện tại hoạt động như nút refresh token
- [ ] hiển thị success / partial success / failed rõ ràng
- [ ] manual fallback vẫn tồn tại nhưng được ẩn hợp lý
- [ ] workspace lỗi auto-refresh được cảnh báo rõ

---

## 17. Kết luận

Khi triển khai theo kế hoạch này, manager sẽ trở thành nơi điều khiển chính cho toàn bộ flow token lifecycle:

- user bấm nút trên card workspace
- manager tự xác định owner phù hợp
- refresher lấy token mới phía sau
- manager update token và sync luôn workspace
- các team sắp hết hạn token được auto-refresh theo batch có kiểm soát
- các trường hợp lỗi vẫn có fallback manual để không làm gián đoạn vận hành

Mục tiêu cuối cùng là đưa trải nghiệm về gần nhất với mong muốn thực tế:
**không còn phải cập nhật token bằng tay như luồng chính nữa, nhưng hệ thống vẫn đủ an toàn, rõ ràng và có đường lui khi automation gặp lỗi.**
