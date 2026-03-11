# 🎨 DESIGN: Realtime Sync V2 for ChatGPT Workspace Manager

Ngày cập nhật: 2026-03-11  
Dựa trên:
- `docs/DESIGN.md` bản cũ (Realtime Auto-Sync phase 1-4)
- `docs/PROJECT_REVIEW_20260311.md`
- Debug finding ngày 2026-03-11 về case: invite accepted nhưng dashboard chưa cập nhật ngay
- Code hiện tại trong `backend/app/services/workspace_sync.py`, `backend/app/routers/invites.py`, `frontend/src/app/page.tsx`

---

## 1. Mục tiêu của bản thiết kế mới

### Vấn đề hiện tại
Bản realtime hiện tại đã có:
- background worker
- SSE event stream
- frontend listener
- auto refetch

Nhưng cơ chế này vẫn còn một khoảng trễ lớn:
- dashboard chỉ biết dữ liệu mới khi backend worker chạy tới lượt
- nếu workspace vừa sync xong thì có thể phải chờ thêm khá lâu mới bị coi là stale
- trường hợp user vừa accept invite bên ngoài tool vẫn có thể không hiện ngay trên dashboard

### Mục tiêu mới
Bản Realtime Sync V2 phải đạt được trải nghiệm sau:

#### Với thay đổi xảy ra **trong tool**
Ví dụ:
- import workspace
- invite member
- resend invite
- revoke invite
- kick member
- manual sync

=> dashboard phải cập nhật **ngay hoặc trong vài giây**.

#### Với thay đổi xảy ra **ngoài tool**
Ví dụ:
- user accept invite ở email/ChatGPT site
- owner/admin khác thao tác trực tiếp ngoài dashboard này

=> dashboard phải cập nhật trong khoảng **5–15 giây với workspace đang “nóng”**, thay vì chờ vài phút hoặc đòi sync tay.

### Kết luận thiết kế
> Mục tiêu thực tế là **near-realtime cực nhanh**, không phải instant 100% tuyệt đối.
>
> Nếu upstream ChatGPT không có webhook/push event chính thức, hệ thống chỉ có thể đạt được realtime bằng **polling thông minh + ưu tiên đúng workspace + SSE để đẩy UI update**.

---

## 2. Quyết định kiến trúc chính

### Quyết định 1: Giữ SSE làm kênh báo tín hiệu cho frontend
Không stream toàn bộ members/invites qua SSE.

SSE chỉ dùng để báo:
- workspace nào đang sync
- sync xong hay chưa
- có lỗi hay không
- tại sao sync vừa chạy

Frontend vẫn refetch bằng API hiện có.

### Quyết định 2: Thay worker polling phẳng bằng **Hot Queue + Smart Polling**
Thay vì tất cả workspace cùng dùng một stale policy đơn giản, mỗi workspace sẽ có:
- độ ưu tiên riêng
- thời hạn follow-up riêng
- nhịp sync riêng trong một khoảng thời gian ngắn sau các event quan trọng

### Quyết định 3: Tách 2 loại sync policy

#### A. Baseline Sync
Dùng để giữ dữ liệu toàn hệ thống không bị quá cũ.

Ví dụ:
- 3–10 phút / lần tùy cấu hình
- áp dụng cho toàn bộ workspace

#### B. Hot Follow-up Sync
Dùng cho workspace vừa có sự kiện đáng chú ý.

Ví dụ:
- vừa invite member
- vừa resend invite
- vừa revoke invite
- vừa kick member
- vừa manual sync
- đang còn pending invite
- vừa có sync fail cần retry

=> các workspace này được poll dày hơn trong một khoảng ngắn.

### Quyết định 4: Action trong tool phải sinh ra “follow-up schedule”
Khi anh thao tác trong dashboard, backend không chỉ update DB local mà còn phải đánh dấu:

> “Workspace này cần được theo dõi sát trong vài phút tới.”

Đây là chìa khóa để bắt case invite vừa accept ngoài tool.

---

## 3. Giải thích dễ hiểu bằng ví dụ đời thường

Hãy tưởng tượng mỗi workspace là một cửa hàng.

### Cách cũ
- cứ 5 phút nhân viên mới đi kiểm tra một vòng
- nên nếu có khách vừa bước vào cửa hàng ngay sau lần kiểm tra trước, dashboard sẽ chưa biết

### Cách mới
- vẫn có một vòng kiểm tra tổng quát cho tất cả cửa hàng
- nhưng cửa hàng nào vừa có tín hiệu quan trọng thì sẽ bị “để mắt” kỹ hơn
- ví dụ trong 2–3 phút đầu sẽ được ghé kiểm tra lại sau 5s, 15s, 30s, 60s...

=> Nhờ vậy, thay đổi thật ngoài đời sẽ lên dashboard nhanh hơn rất nhiều.

---

## 4. Thiết kế dữ liệu

## 4.1. Dữ liệu lưu lâu trong database

### Bảng `workspaces`
Đã có:
- `org_id`
- `name`
- `status`
- `member_count`
- `member_limit`
- `last_sync`
- `sync_error`
- `sync_started_at`
- `sync_finished_at`

### Đề xuất thêm cho V2

| Field | Kiểu | Ý nghĩa đời thường |
|------|------|---------------------|
| `next_sync_at` | datetime/null | lần hẹn kiểm tra tiếp theo của workspace |
| `sync_priority` | integer | mức ưu tiên sync của workspace |
| `hot_until` | datetime/null | theo dõi sát workspace này đến khi nào |
| `last_activity_at` | datetime/null | workspace này vừa có biến động quan trọng lúc nào |
| `sync_reason` | string/null | lý do lần sync gần nhất được lên lịch |

### Giải thích ngắn
- `next_sync_at`: giúp worker biết workspace nào cần kiểm tra trước
- `sync_priority`: workspace nóng được chạy trước workspace lạnh
- `hot_until`: chỉ rõ giai đoạn “đang nóng” còn kéo dài bao lâu
- `last_activity_at`: phục vụ debug và quan sát hành vi hệ thống
- `sync_reason`: giúp log/UI biết sync do invite, manual, retry hay baseline

> Nếu anh muốn giữ DB gọn ở phiên bản đầu của V2, có thể triển khai `next_sync_at`, `hot_until`, `sync_reason` trước; `sync_priority` có thể suy ra từ rule.

---

## 4.2. Dữ liệu chỉ lưu tạm trong memory backend

```text
┌─────────────────────────────────────────────────────────────┐
│ Runtime Memory                                              │
├─────────────────────────────────────────────────────────────┤
│ per-workspace lock                                          │
│ SSE subscribers                                             │
│ event sequence counter                                      │
│ local retry window cache (optional)                         │
└─────────────────────────────────────────────────────────────┘
```

### Dùng cho
- tránh sync chồng lên nhau
- phát event đúng thứ tự
- giữ retry/backoff nhẹ nếu cần

### Không nên lạm dụng memory cho core schedule
Core schedule nên nằm trong DB (`next_sync_at`, `hot_until`) để:
- restart app không mất lịch
- debug được rõ ràng hơn
- dễ mở rộng về sau

---

## 5. Trạng thái của một workspace trong V2

```text
idle → scheduled → syncing → synced
                 ↘        ↘
                  hot       error
```

### Diễn giải

| State | Nghĩa đời thường |
|-------|------------------|
| `idle` | workspace đang yên ổn |
| `scheduled` | đã được xếp lịch sync |
| `syncing` | đang kiểm tra thật |
| `synced` | vừa cập nhật xong |
| `hot` | đang bị theo dõi sát vì mới có biến động |
| `error` | lần kiểm tra gần nhất bị lỗi |

### Quy tắc đơn giản
- action quan trọng → `scheduled` + `hot_until`
- worker chạy → `syncing`
- sync xong → `synced`
- nếu vẫn còn lý do cần theo dõi sát → giữ `hot`
- nếu fail → `error` + retry sớm có giới hạn

---

## 6. Luồng hoạt động tổng quát mới

```text
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND DASHBOARD                                          │
│ - Gọi API                                                   │
│ - Nghe SSE                                                  │
│ - Khi có event thì refetch dữ liệu liên quan                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ FASTAPI API + SSE                                            │
│ - Nhận action của user                                       │
│ - Xếp lịch follow-up sync cho workspace                      │
│ - Worker xử lý lịch sync                                     │
│ - Phát event ra frontend                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ SYNC SCHEDULER / HOT QUEUE                                   │
│ - Chọn workspace tới hạn                                     │
│ - Ưu tiên workspace hot                                      │
│ - Retry/backoff nếu lỗi                                      │
│ - Hạ nhiệt workspace khi không còn biến động                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ CHATGPT UPSTREAM + LOCAL DB                                  │
│ - Lấy members/invites                                        │
│ - Ghi về DB local                                            │
│ - So sánh diff                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Thiết kế hành trình chính

## 7.1. Hành trình 1: User invite member trong dashboard

1. User bấm invite
2. Backend gọi upstream để tạo invite
3. Backend lưu invite vào DB local
4. Backend gọi `schedule_followup_sync(org_id, reason="invite_created")`
5. Workspace được gắn `hot_until = now + HOT_WINDOW`
6. `next_sync_at` được đặt rất gần (ví dụ 5 giây)
7. Worker chạy tới lượt, sync members + invites
8. Nếu user bên ngoài đã accept nhanh:
   - member mới sẽ được kéo về local DB
9. Backend phát `workspace_updated`
10. Frontend refetch và dashboard cập nhật

### Ý nghĩa
Ngay sau action invite, workspace sẽ được theo dõi sát trong một khoảng ngắn, thay vì quay về chu kỳ 5 phút chung.

---

## 7.2. Hành trình 2: User accept invite ngoài tool

1. Tool trước đó đã tạo invite hoặc detect pending invite
2. Workspace đang ở trạng thái hot
3. Worker chạy follow-up sync theo chu kỳ ngắn
4. Upstream trả về member mới đã accept
5. Backend cập nhật local DB
6. Invite pending có thể biến mất hoặc member count tăng
7. Backend phát event `workspace_updated`
8. Frontend đang mở dashboard nhận event và reload ngay

### Mục tiêu UX
- thường thấy thay đổi sau 5–15 giây
- không cần F5 nhiều lần
- không phải sync tay trong đa số case

---

## 7.3. Hành trình 3: Workspace lạnh lâu ngày

1. Workspace không có action mới
2. Không còn pending invite
3. `hot_until` hết hạn
4. Workspace quay lại baseline schedule
5. Worker chỉ sync theo chu kỳ chậm hơn

### Ý nghĩa
Giữ hệ thống nhẹ hơn, không poll dày toàn bộ workspace vô ích.

---

## 7.4. Hành trình 4: Sync lỗi / token fail / upstream fail

1. Worker bắt đầu sync
2. Upstream lỗi hoặc token hết hạn
3. Backend ghi `status = error`, `sync_error`
4. Backend phát `sync_failed`
5. Scheduler đặt `next_sync_at` retry theo backoff ngắn có giới hạn
6. Nếu lỗi lặp lại quá nhiều:
   - workspace rời hot mode
   - chờ manual intervention hoặc baseline retry

### Ý nghĩa
Không để lỗi gây vòng lặp spam request vô hạn.

---

## 8. Scheduler design (phần quan trọng nhất)

## 8.1. Các loại lịch sync

### A. Immediate follow-up
Áp dụng ngay sau action mạnh:
- import workspace
- invite
- resend invite
- revoke invite
- kick member
- manual sync thành công

Ví dụ:
- sync sau 5s
- rồi 15s
- rồi 30s
- rồi 60s
- rồi quay về baseline nếu không còn nóng

### B. Pending-invite watch
Nếu workspace còn `pending_invites > 0`, giữ workspace trong chế độ hot thêm một khoảng thời gian.

Ví dụ:
- cứ 15–30s poll lại
- tối đa 3–10 phút tùy config

### C. Baseline refresh
Áp dụng cho mọi workspace để chống stale lâu ngày.

Ví dụ:
- 3–10 phút / lần

---

## 8.2. Đề xuất rule đơn giản cho phiên bản đầu của V2

### Config đề xuất

| Biến | Gợi ý ban đầu | Ý nghĩa |
|------|---------------|---------|
| `SYNC_LOOP_INTERVAL_SECONDS` | 5 | worker thức dậy mỗi 5 giây |
| `SYNC_BASELINE_MINUTES` | 5 | workspace bình thường sync 5 phút/lần |
| `SYNC_HOT_WINDOW_SECONDS` | 180 | workspace nóng được theo dõi sát trong 3 phút |
| `SYNC_FOLLOWUP_STEPS` | `5,15,30,60` | các mốc follow-up sau action |
| `SYNC_PENDING_INVITE_INTERVAL_SECONDS` | 15 | nếu còn pending invite thì check lại mỗi 15 giây |
| `SYNC_ERROR_RETRY_STEPS` | `10,30,60` | retry backoff sau lỗi |
| `SYNC_MAX_PARALLEL_WORKSPACES` | 2 hoặc 3 | tránh gọi upstream quá dày |

### Vì sao worker loop có thể giảm xuống 5 giây?
Vì loop chạy thường xuyên không có nghĩa là sync mọi workspace mỗi 5 giây.

Loop chỉ làm việc này:
- nhìn xem workspace nào đến hạn `next_sync_at`
- chọn vài workspace nóng nhất
- sync đúng những workspace đó

=> nhanh nhưng vẫn tiết kiệm.

---

## 8.3. Hàm xếp lịch đề xuất

### `schedule_followup_sync(org_id, reason, steps=None)`
Nhiệm vụ:
- đặt `hot_until`
- đặt `next_sync_at`
- cập nhật `sync_reason`
- ưu tiên workspace cho worker

### Pseudo logic
```text
if workspace not found:
    return

workspace.last_activity_at = now
workspace.hot_until = max(existing_hot_until, now + HOT_WINDOW)
workspace.next_sync_at = min(existing_next_sync_at, now + first_followup_step)
workspace.sync_reason = reason
save
publish workspace_schedule_updated (optional)
```

### Các reason nên có
- `manual_sync`
- `invite_created`
- `invite_resend`
- `invite_cancelled`
- `member_kicked`
- `pending_invite_watch`
- `baseline_refresh`
- `retry_after_error`

---

## 8.4. Hàm chọn workspace tới hạn

### `pick_due_workspaces(now, limit)`
Ưu tiên theo thứ tự:
1. workspace đang hot và đã tới `next_sync_at`
2. workspace lỗi cần retry
3. workspace baseline quá hạn

### Sort gợi ý
- `sync_priority` giảm dần
- `next_sync_at` tăng dần
- `last_activity_at` mới hơn được ưu tiên hơn

---

## 9. API / Cửa giao tiếp cần có

## 9.1. API hiện có tiếp tục dùng
- `GET /api/workspaces`
- `GET /api/workspaces/{id}/members`
- `GET /api/invites?org_id=...`
- `GET /api/workspaces/{id}/sync`
- `POST /api/invite`
- `POST /api/resend-invite`
- `DELETE /api/cancel-invite`
- `DELETE /api/member`

## 9.2. API không cần thêm mới ở bản đầu V2
Bản đầu có thể **không cần endpoint mới cho UI**, chỉ cần backend schedule tốt hơn.

## 9.3. Event SSE nên mở rộng thêm
Ngoài các event hiện có:
- `sync_started`
- `workspace_updated`
- `sync_failed`
- `heartbeat`

Nên cân nhắc thêm:
- `workspace_scheduled`
- `workspace_hot_state_changed`

### Ý nghĩa
Không bắt buộc cho logic chạy, nhưng rất tốt cho:
- debug
- hiển thị trạng thái “đang theo dõi sát” trên UI
- hiểu vì sao workspace đang tự refresh nhiều hơn bình thường

---

## 10. Thiết kế frontend

## 10.1. Dashboard cần hiển thị gì thêm?

### Tối thiểu
- trạng thái `syncing`
- last sync
- sync error

### Nên thêm trong V2
- badge nhỏ: `Hot` / `Watching invites`
- subtitle: `Đang theo dõi sát vì vừa có lời mời mới`

Điều này giúp user hiểu:
- vì sao workspace đang update nhanh
- tool đang làm việc chứ không phải bị lag

---

## 10.2. Frontend xử lý event như thế nào?

### Quy tắc mới
- `workspace_scheduled` → chỉ update badge/trạng thái nhẹ, không cần refetch full ngay
- `sync_started` → update syncing state
- `workspace_updated` → refetch list + detail liên quan
- `sync_failed` → refetch list + toast lỗi nhẹ
- `heartbeat` → bỏ qua

### Debounce vẫn cần giữ
Vì V2 có thể sinh nhiều event hơn bản cũ.

Frontend phải:
- gom refresh theo `org_id`
- không refetch trùng quá dày
- giữ SSE connection ổn định

---

## 10.3. Dashboard summary
Summary phải tiếp tục tính từ dữ liệu aggregate backend:
- `total teams`
- `members`
- `pending invites`
- `sync errors`

Không nên phụ thuộc việc expand card.

---

## 11. Thiết kế backend theo từng khu vực code

## 11.1. `backend/app/models.py`
Thêm field mới vào `Workspace`:
- `next_sync_at`
- `hot_until`
- `last_activity_at`
- `sync_reason`
- (optional) `sync_priority`

## 11.2. `backend/app/db.py`
Thêm migration nhẹ để bổ sung cột mới cho DB cũ.

## 11.3. `backend/app/services/workspace_sync.py`
Tách rõ các lớp logic:
- `schedule_followup_sync(...)`
- `mark_workspace_hot(...)`
- `pick_due_workspaces(...)`
- `apply_post_sync_schedule(...)`
- `run_sync_cycle(...)`

### `apply_post_sync_schedule(...)` nên làm gì?
Sau mỗi sync thành công:
- nếu vẫn còn pending invite → lên lịch sync lại sớm
- nếu workspace vẫn đang hot → dùng step kế tiếp trong follow-up chain
- nếu đã ổn định → quay về baseline

## 11.4. `backend/app/routers/invites.py`
Sau khi:
- invite
- resend
- cancel

phải gọi `schedule_followup_sync(...)`

## 11.5. `backend/app/routers/members.py`
Sau khi kick member thành công:
- gọi `schedule_followup_sync(...)`

## 11.6. `backend/app/routers/workspaces.py`
Sau manual sync hoặc import thành công:
- kích hoạt hot follow-up schedule ngắn hạn

## 11.7. `backend/app/services/events.py`
Không cần thay kiến trúc broker ở bản đầu V2.
Nhưng nên giữ khả năng phát thêm event nhẹ như `workspace_scheduled`.

---

## 12. Checklist kiểm tra hoàn thành (Acceptance Criteria)

## Tính năng: Realtime Sync V2

### ✅ Cơ bản
- [ ] Sau khi invite member, workspace được đưa vào follow-up sync schedule
- [ ] Sau khi resend invite, workspace được follow-up lại
- [ ] Sau khi cancel invite, workspace được refresh sớm để local state khớp upstream
- [ ] Sau khi kick member, workspace được refresh sớm
- [ ] Workspace có pending invite được poll dày hơn workspace bình thường
- [ ] Workspace bình thường không bị poll quá dày
- [ ] Frontend vẫn nhận SSE ổn định, không reconnect churn

### ✅ Trải nghiệm
- [ ] Trường hợp accept invite ngoài tool thường được phản ánh trên dashboard trong 5–15 giây
- [ ] User không cần bấm sync tay trong phần lớn các case invite/member change
- [ ] UI hiển thị rõ workspace đang được theo dõi sát
- [ ] Toast không bị spam khi follow-up sync chạy nhiều nhịp

### ✅ An toàn hệ thống
- [ ] Không có 2 sync cùng chạy chồng trên một workspace
- [ ] Worker không sync tất cả workspace mỗi 5 giây
- [ ] Có giới hạn số workspace xử lý song song
- [ ] Retry lỗi có backoff, không loop vô hạn

### ✅ Dễ debug
- [ ] Log cho biết workspace được schedule vì reason nào
- [ ] Có thể nhìn DB để hiểu workspace đang hot hay baseline
- [ ] SSE event đủ để frontend và developer quan sát trạng thái

---

## 13. Test cases thiết kế trước khi code

### TC-01: Invite → accept nhanh bên ngoài → dashboard tự cập nhật
**Given:** Workspace vừa gửi invite từ dashboard  
**When:** User accept invite ngoài hệ thống trong vòng 10–20 giây  
**Then:**
- workspace được follow-up sync sớm
- member mới xuất hiện trên dashboard mà không cần sync tay
- pending invite giảm hoặc biến mất

### TC-02: Workspace lạnh không bị sync quá dày
**Given:** Workspace không có action mới, không pending invite  
**When:** Worker loop chạy nhiều vòng  
**Then:**
- workspace chỉ được sync theo baseline schedule
- không có spam request lên upstream

### TC-03: Invite pending kéo dài
**Given:** Workspace còn pending invite chưa ai accept  
**When:** Worker chạy trong hot window  
**Then:**
- workspace được re-check theo pending invite interval
- sau khi hết hot window thì quay về baseline nếu không còn lý do nóng khác

### TC-04: Kick member
**Given:** Owner kick một member trong dashboard  
**When:** API kick thành công  
**Then:**
- workspace được xếp lịch follow-up sync ngay
- dashboard phản ánh member count mới sớm

### TC-05: Sync lỗi liên tiếp
**Given:** Upstream đang lỗi tạm thời  
**When:** Worker sync thất bại 2–3 lần  
**Then:**
- retry theo backoff
- không loop vô hạn mỗi vài giây
- UI vẫn thấy trạng thái error rõ ràng

### TC-06: SSE reconnect trong khi workspace vẫn hot
**Given:** Browser bị mất mạng ngắn rồi reconnect  
**When:** SSE kết nối lại thành công  
**Then:**
- frontend reload list workspaces
- workspace đang hot vẫn được hiển thị đúng trạng thái
- không miss cập nhật quan trọng kéo dài

---

## 14. Kế hoạch implement khuyến nghị

## Phase A — Nền tảng scheduler
- thêm cột DB mới
- thêm schedule API nội bộ (`schedule_followup_sync`)
- thêm `pick_due_workspaces`
- đổi worker sang đọc `next_sync_at`

## Phase B — Gắn scheduler vào các action
- invite / resend / cancel
- kick member
- import workspace
- manual sync

## Phase C — UI + SSE polish
- thêm hot badge / reason text
- thêm SSE event cho schedule change nếu cần
- chống spam toast mạnh hơn

## Phase D — Test + tuning
- test scheduler logic
- test transition hot → baseline
- test follow-up after invite
- tuning env config thực tế

---

## 15. Quyết định không làm ngay ở V2 đầu tiên
- Không chuyển sang WebSocket
- Không thêm Redis queue ở phiên bản đầu
- Không cố stream toàn bộ diff dữ liệu qua SSE
- Không cố “instant 100%” nếu upstream không hỗ trợ webhook

---

## 16. Gợi ý cấu hình ban đầu để chạy thử

```env
SYNC_LOOP_INTERVAL_SECONDS=5
SYNC_BASELINE_MINUTES=5
SYNC_HOT_WINDOW_SECONDS=180
SYNC_FOLLOWUP_STEPS=5,15,30,60
SYNC_PENDING_INVITE_INTERVAL_SECONDS=15
SYNC_ERROR_RETRY_STEPS=10,30,60
SYNC_MAX_PARALLEL_WORKSPACES=2
```

### Cách hiểu nhanh
- worker tỉnh dậy mỗi 5 giây
- nhưng không sync bừa toàn bộ
- chỉ sync workspace đang tới hạn
- workspace nóng được chăm sát hơn
- workspace lạnh vẫn nhẹ nhàng

---

## 17. Kết luận ngắn

Realtime Sync V2 không phải là “đập đi làm lại”.  
Nó là bước nâng cấp thông minh từ nền tảng hiện có:

- giữ SSE
- giữ API cũ
- giữ shared sync service
- thêm scheduler tốt hơn
- thêm hot queue/follow-up sync

> Nếu làm đúng bản thiết kế này, tool sẽ chuyển từ:
> “có auto-sync nhưng đôi lúc vẫn chậm”
>
> sang:
> “dashboard phản ứng nhanh với thay đổi thật, gần như không còn phụ thuộc sync tay nữa”.

---

*Tạo/cập nhật bởi AWF Design Phase - Realtime Sync V2*
