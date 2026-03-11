# Changelog

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

### Fixed
- Clarified the backend test workflow to avoid the misleading `python -m pytest backend/tests` invocation from repo root
- Stabilized frontend test expectations against the current workspace/member/invite UI
- Corrected seat-limit warning behavior in the member table

### Cleaned
- Repository cleanup pass prepared for removal of generated test databases, Python caches, and transient logs
