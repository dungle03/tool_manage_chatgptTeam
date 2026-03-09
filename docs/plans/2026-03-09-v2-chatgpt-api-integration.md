# 📋 Plan v2: ChatGPT Team Manager — Real API Integration

**Date:** 2026-03-09
**Status:** Draft
**Ref repo:** [tibbar213/team-manage](https://github.com/tibbar213/team-manage)
**Ref UI:** Screenshot từ user (accordion workspace + member table)

---

## 1. Mục tiêu

Build tool quản lý workspace ChatGPT Team **thật**, gọi ChatGPT internal API qua Access Token, hiển thị UI giống hình mẫu.

### Khác biệt so với v1

|             | v1 (hiện tại)         | v2 (plan này)                                                        |
| ----------- | --------------------- | -------------------------------------------------------------------- |
| Data source | Local SQLite thủ công | **ChatGPT API thật**                                                 |
| Token auth  | Fake Bearer token     | **AT Token (Access Token) from ChatGPT**                             |
| Sync        | Không có              | **Auto-sync members realtime**                                       |
| UI layout   | Grid cards + table    | **Accordion workspace + inline table**                               |
| Actions     | Kick only             | **Duyệt (Approve invite), Hủy (Cancel invite), Xóa (Delete member)** |
| Language    | English               | **Vietnamese**                                                       |

---

## 2. ChatGPT Internal API Endpoints (từ reference repo)

Base URL: `https://chatgpt.com/backend-api`

### 2.1 Authentication

```
GET https://chatgpt.com/api/auth/session
Cookie: __Secure-next-auth.session-token=<SESSION_TOKEN>
→ Returns: { accessToken, sessionToken }
```

### 2.2 Get Account Info (tìm Team workspace)

```
GET /accounts/check/v4-2023-04-27
Authorization: Bearer <ACCESS_TOKEN>
→ Returns: { accounts: { [account_id]: { account, entitlement } } }
    → Filter plan_type == "team"
    → Extract: account_id, name, subscription_plan, expires_at, member count
```

### 2.3 Get Members

```
GET /accounts/{account_id}/users?limit=50&offset=0
Authorization: Bearer <ACCESS_TOKEN>
→ Returns: { items: [...members], total }
→ Member fields: id, email, name, role, created, picture
```

### 2.4 Get Invites (pending)

```
GET /accounts/{account_id}/invites
Authorization: Bearer <ACCESS_TOKEN>
chatgpt-account-id: <account_id>
→ Returns: { items: [...invites] }
```

### 2.5 Send Invite

```
POST /accounts/{account_id}/invites
Authorization: Bearer <ACCESS_TOKEN>
chatgpt-account-id: <account_id>
Body: { "email_addresses": ["user@email.com"], "role": "standard-user", "resend_emails": true }
```

### 2.6 Cancel Invite (Hủy)

```
DELETE /accounts/{account_id}/invites
Authorization: Bearer <ACCESS_TOKEN>
chatgpt-account-id: <account_id>
Body: { "email_address": "user@email.com" }
```

### 2.7 Delete Member (Xóa)

```
DELETE /accounts/{account_id}/users/{user_id}
Authorization: Bearer <ACCESS_TOKEN>
chatgpt-account-id: <account_id>
```

### 2.8 Refresh Token

```
GET https://chatgpt.com/api/auth/session?exchange_workspace_token=true&workspace_id={account_id}
Cookie: __Secure-next-auth.session-token=<SESSION_TOKEN>
```

---

## 3. UI Design (theo hình mẫu)

### 3.1 Layout tổng thể

```
┌──────────────────────────────────────────────────────┐
│  🏢 ChatGPT Team Manager          [+ Thêm Team]     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ▼ 666     [SỐNG] 1s   ████████░░ 4/7  [+][✏️][🗑️] │
│  ┌──────────────────────────────────────────────────┐│
│  │ □ # │ EMAIL           │ ACCOUNT │ ROLE  │ NGÀY  ││
│  │─────┼─────────────────┼─────────┼───────┼───────││
│  │ □ 1 │ admin@robin...  │ ChatGPT │ 👑Owner│ 6/3  ││
│  │ □ 2 │ user1@gmail.com │ John    │ 👤User │ 7/3  ││
│  │ ... │ pending@mail... │ —       │ ⏳Pend │ 7/3  ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│  ▶ IDconcepts [SỐNG] 1s  ████████░░ 5/7 [+][✏️][🗑️]│
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 3.2 Workspace Header

- Tên workspace (collapse/expand)
- Badge: `SỐNG` (green) / `LỖI` (red) / `HẾT HẠN` (grey)
- Sync time: last sync elapsed (e.g., "1s", "5m")
- Progress bar: members / member_limit
- Toolbar: [+ Mời], [✏️ Sửa], [🗑️ Xóa workspace]

### 3.3 Member Table

| Column       | Source    | Note                                  |
| ------------ | --------- | ------------------------------------- |
| Checkbox     | UI        | Multi-select                          |
| #            | Row index | Auto-number                           |
| EMAIL        | API       | Color: blue = active, grey = pending  |
| ACCOUNT NAME | API       | Member name                           |
| ROLE         | API       | Owner (👑) / User (👤) / Pending (⏳) |
| NGÀY MỜI     | API       | created_at formatted                  |
| ACTION       | UI        | Duyệt/Hủy cho pending, Xóa cho member |

### 3.4 Action Buttons

| Button            | Khi nào hiện                    | API call                            |
| ----------------- | ------------------------------- | ----------------------------------- |
| **Duyệt** (green) | Member đã join nhưng chưa duyệt | Local approve                       |
| **Hủy** (red)     | Invite pending                  | `DELETE /accounts/{id}/invites`     |
| **Xóa** (red)     | Member active (non-owner)       | `DELETE /accounts/{id}/users/{uid}` |

---

## 4. Architecture v2

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Frontend   │──────▶│  Backend (FastAPI)│──────▶│  ChatGPT API     │
│  Next.js    │ REST  │  Python           │ HTTP  │  chatgpt.com     │
│  localhost:3│       │  localhost:8000    │       │  /backend-api    │
└─────────────┘       └────────┬─────────┘       └──────────────────┘
                               │
                         ┌─────┴──────┐
                         │ SQLite DB  │
                         │ (cache +   │
                         │  tokens)   │
                         └────────────┘
```

### Backend cần thay đổi:

1. **`chatgpt_service.py`** (MỚI) — Gọi ChatGPT API, xử lý token, retry
2. **`models.py`** — Thêm fields: `access_token`, `session_token`, `account_id`, `last_sync`
3. **`routers/`** — Sửa endpoints: gọi ChatGPT API thay vì CRUD local
4. **`auth.py`** — Giữ admin auth cho dashboard

### Frontend cần thay đổi:

1. **`page.tsx`** — Chuyển từ grid → accordion layout
2. **Components** — Redesign theo hình mẫu (checkbox, row numbers, Vietnamese labels)
3. **CSS** — Cập nhật cho accordion + inline table

---

## 5. Implementation Phases

### Phase 1: Backend — ChatGPT API Service ⬜

**Tasks:**

- [ ] Tạo `backend/app/services/chatgpt_service.py`
  - HTTP client với retry + exponential backoff
  - Session pool (per account_id)
  - Proxy support (optional)
- [ ] Implement các method:
  - `refresh_token(session_token) → access_token`
  - `get_account_info(access_token) → team accounts`
  - `get_members(access_token, account_id) → members[]`
  - `get_invites(access_token, account_id) → invites[]`
  - `send_invite(access_token, account_id, email)`
  - `delete_invite(access_token, account_id, email)`
  - `delete_member(access_token, account_id, user_id)`
- [ ] Thêm `curl-cffi` hoặc `httpx` vào requirements.txt
- [ ] Test với mock hoặc token thật

### Phase 2: Backend — Model + API Update ⬜

**Tasks:**

- [ ] Update `models.py`:
  - `Team` model: `account_id`, `name`, `access_token`, `session_token`, `status`, `member_count`, `member_limit`, `last_sync`, `expires_at`
- [ ] Sửa routers:
  - `GET /api/teams` → list teams from DB (cached)
  - `POST /api/teams/import` → import AT token, auto-detect team info
  - `GET /api/teams/{id}/sync` → call ChatGPT API, update cache
  - `GET /api/teams/{id}/members` → call ChatGPT API get_members
  - `GET /api/teams/{id}/invites` → call ChatGPT API get_invites
  - `POST /api/teams/{id}/invite` → call ChatGPT API send_invite
  - `DELETE /api/teams/{id}/invite` → call ChatGPT API delete_invite
  - `DELETE /api/teams/{id}/members/{uid}` → call ChatGPT API delete_member
- [ ] Auto-sync background task (optional)
- [ ] Token encrypt/decrypt cho security

### Phase 3: Frontend — Accordion UI ⬜

**Tasks:**

- [ ] Redesign `page.tsx` → accordion workspace list
- [ ] `WorkspaceAccordion` component:
  - Expandable header: name, status badge, sync time, progress bar, toolbar
  - Collapse/expand animation
- [ ] `MemberTable` update:
  - Add checkbox column
  - Add row numbers
  - Vietnamese labels (EMAIL, TÊN TÀI KHOẢN, VAI TRÒ, NGÀY MỜI, HÀNH ĐỘNG)
  - Color-coded emails (active = blue, pending = grey)
  - Role icons (👑 Owner, 👤 User, ⏳ Pending)
- [ ] Action buttons: Duyệt (green), Hủy (red), Xóa (red)
- [ ] Import team dialog (nhập AT token)

### Phase 4: Frontend — Polish + Testing ⬜

**Tasks:**

- [ ] Loading states khi sync
- [ ] Error handling + toast notifications
- [ ] Confirm dialogs cho delete/kick
- [ ] Responsive design
- [ ] Update backend + frontend tests
- [ ] Commit + push

---

## 6. Yêu cầu từ user

Trước khi code, cần anh cung cấp:

| Thông tin                               | Cần?        | Ghi chú                                                           |
| --------------------------------------- | ----------- | ----------------------------------------------------------------- |
| **Session Token** hoặc **Access Token** | ✅ BẮT BUỘC | Lấy từ cookie `__Secure-next-auth.session-token` trên chatgpt.com |
| **Proxy** (nếu cần)                     | ⚠️ Optional | HTTP/SOCKS5 proxy URL nếu bị block                                |
| Triển khai ở đâu?                       | 📝 Later    | Local dev trước, Docker sau                                       |

### Cách lấy Session Token:

1. Mở https://chatgpt.com và đăng nhập
2. F12 → Application → Cookies → chatgpt.com
3. Copy giá trị `__Secure-next-auth.session-token`
4. Dán vào file `.env`: `SESSION_TOKEN=eyJhbGci...`

---

## 7. Phụ thuộc mới

### Backend

```
curl-cffi          # HTTP client bypass Cloudflare (như reference repo)
pyjwt              # Parse JWT token để extract email/account
cryptography       # Encrypt stored tokens
```

### Frontend

- Không thêm dependency mới, chỉ sửa CSS + components

---

## 8. Lộ trình

| Phase                    | Ước lượng | Phụ thuộc     |
| ------------------------ | --------- | ------------- |
| Phase 1: ChatGPT Service | 2-3h      | Token từ user |
| Phase 2: Backend API     | 1-2h      | Phase 1       |
| Phase 3: Accordion UI    | 2-3h      | Phase 2       |
| Phase 4: Polish          | 1h        | Phase 3       |
| **Tổng**                 | **~8h**   |               |

---

## 9. Rủi ro

| Rủi ro               | Mức độ        | Giải pháp                                |
| -------------------- | ------------- | ---------------------------------------- |
| ChatGPT API thay đổi | 🟡 Trung bình | Theo dõi reference repo updates          |
| Cloudflare block     | 🔴 Cao        | Dùng `curl-cffi` với browser fingerprint |
| Token hết hạn        | 🟡 Trung bình | Auto-refresh bằng session_token          |
| Rate limit           | 🟡 Trung bình | Retry + exponential backoff              |
