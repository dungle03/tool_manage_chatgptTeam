# Changelog

## [2026-04-09]

### Added

- Script `backend/export_workspace_members.py` để export team/member từ local database sang CSV hoặc JSON
- `README.en.md` làm bản tài liệu tiếng Anh song song với README chính
- Regression test `backend/tests/test_invite_router_regressions.py` để khóa lỗi invite idempotency

### Changed

- `README.md` được viết lại theo hướng chuyên nghiệp hơn và giữ tiếng Việt làm mặc định
- Background token refresh phát SSE event riêng cho success/failure để frontend toast hiển thị đầy đủ
- Auto-kick member normalization hỗ trợ nhiều field ID hơn từ payload upstream
- `.gitignore` được bổ sung `backend/exports/` để tránh commit file export sinh ra
- Đồng bộ lại local project memory trong `.brain/` sau khi hoàn tất stabilization và push

### Fixed

- Tránh lỗi `UNIQUE constraint failed` khi tạo invite trùng `invite_id` từ upstream
- Khôi phục luồng toast realtime cho auto refresh token sau refactor
- Sửa case auto-kick chỉ cảnh báo nhưng không kick được khi upstream trả member ID theo field khác
- Banner unauthorized phía frontend chỉ còn hiển thị finding còn active, giảm nhầm lẫn trong vận hành

## [2026-04-03]

### Added

- `Invite.created_by_tool` provenance flag để phân biệt invite do tool tạo với invite sync từ remote
- Regression test `test_external_pending_invite_guard.py` để khóa case pending invite từ người khác không được whitelist
- Regression test `test_kick_member_regression.py` để khóa các hành vi quan trọng của flow kick member

### Changed

- Logic whitelist của auto-kick giờ chỉ tin tưởng:
  - member đã tồn tại trong local DB
  - pending invite do chính tool tạo
- Route invite và sync pipeline đồng bộ metadata `created_by_tool` xuyên suốt từ lúc tạo invite đến lúc sync remote
- Đồng bộ lại project memory sau khi rà full backend suite lần cuối

### Fixed

- Chặn trường hợp pending invite do thành viên khác mời bị hiểu nhầm là hợp lệ sau khi accept vào team
- Cập nhật test realtime invite route để khớp signature mới của `send_invite(..., resend_emails=...)`
- Xác nhận full backend suite pass `60/60` sau đợt siết logic cuối

## [2026-03-20]

### Changed

- Compact workspace card hiển thị thêm dòng `Team expires on` bên dưới `Access token expires in ...`

### Fixed

- Sửa lỗi rename workspace/team bị 502 do backend shared request helper chưa hỗ trợ method `PATCH`
- Cập nhật regression test ChatGPT service và fake async session helper để verify PATCH request đúng cách

## [2026-03-18]

### Added

- Workspace token update flow với endpoint backend `PATCH /api/workspaces/{id}/token`
- Dialog `update-token-dialog.tsx` để dán access token mới cho từng workspace
- Nút action key trên cả `WorkspaceCard` và `CompactWorkspaceCard`

### Changed

- Dashboard mặc định mở ở mode 2 / compact view
- Icon action update token được đổi sang chìa khóa màu vàng theo quyết định UI cuối cùng
- Đồng bộ lại project memory trong `.brain/` sau khi hoàn tất feature và push sạch repo

### Fixed

- Hoàn thiện refresh UI sau khi cập nhật token để summary/workspace state được cập nhật ngay
- Đồng bộ backend/frontend types cho mutation update token

## [2026-03-12]

### Added

- Root helper script `run_backend_tests.ps1` to run backend pytest from the correct working directory
- Updated project review for the current repository state
- Persistent project-memory updates under `.brain/`

### Changed

- Polished repository README for public/internal repo handoff
- Workspace default seat limit aligned to **7 members**
- Over-limit member warning now starts from the **8th active member**
- Frontend tests updated to reflect the current UI and business rules
- Project review and project-memory documents refreshed to match the latest implementation state
- README chính của repository được đổi lại sang **tiếng Việt** theo quyết định cuối cùng
- Đồng bộ lại local project memory với một lần `/save_brain` cuối trước khi push

### Fixed

- Clarified the backend test workflow to avoid the misleading `python -m pytest backend/tests` invocation from repo root
- Stabilized frontend test expectations against the current workspace/member/invite UI
- Corrected seat-limit warning behavior in the member table

### Cleaned

- Repository cleanup pass prepared for removal of generated test databases, Python caches, and transient logs
